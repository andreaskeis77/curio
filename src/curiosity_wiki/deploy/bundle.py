"""Bundle-Builder fuer VPS-Deployment (ADR-0017).

Erzeugt ein ZIP mit:

- ``manifest.json`` (Schema-Version, Hashes, bytes_total, git_sha optional)
- ``wiki/``  — Markdown-Pages aus ``wiki/``
- ``read_models/`` — gebaute Read-Models
- ``prompts/`` — Prompt-Registry
- ``eval/`` — Goldens
- ``data/registry/curiosity.sqlite`` — bereinigte Kopie (private Sources entfernt)
- ``pyproject.toml``, ``src/``, ``README.md`` — fuer Re-Install auf VPS

Nicht enthalten:

- ``raw/`` (immer)
- ``proposals/``, ``extracted/``, ``docs/_ops/``, ``.env``, ``.venv/``,
  ``__pycache__/``, SQLite-WAL-/SHM-Files

Fuer SQLite wird ``VACUUM INTO`` benutzt — das produziert eine konsistente
Kopie ohne private Source-Reihen.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import shutil
import sqlite3
import zipfile
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from curiosity_wiki import __version__
from curiosity_wiki.paths import VaultPaths, get_paths
from curiosity_wiki.registry import connect

BUNDLE_SCHEMA_VERSION = 1

# Whitelist: relative Pfade (oder Verzeichnis-Praefixe), die ins Bundle wandern.
INCLUDE_DIRS = ("wiki", "read_models", "prompts", "eval", "src")
INCLUDE_FILES = ("pyproject.toml", "README.md")

# Blacklist (substring-match auf Posix-Pfad). Wins ueber Whitelist.
EXCLUDE_PATTERNS = (
    "raw/",
    "proposals/",
    "extracted/",
    "docs/_ops/",
    ".env",
    ".venv/",
    "__pycache__/",
    ".sqlite-wal",
    ".sqlite-shm",
    ".pytest_cache/",
    "node_modules/",
    "/.git/",
    ".tmp",
)


@dataclass
class BundleResult:
    """Ergebnis eines Bundle-Builds."""

    bundle_path: str
    manifest_path: str  # Pfad innerhalb des Bundles
    files_count: int = 0
    bytes_total: int = 0
    sanitized_sources_removed: int = 0
    git_sha: str | None = None
    skipped: list[tuple[str, str]] = field(default_factory=list)


def _sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _is_excluded(rel_path: str) -> bool:
    rel_norm = rel_path.replace("\\", "/")
    return any(pattern in rel_norm or rel_norm.endswith(pattern) for pattern in EXCLUDE_PATTERNS)


def _walk_included(paths: VaultPaths) -> list[Path]:
    """Liefert alle Files, die nach Whitelist erfasst und nicht von Blacklist gekickt werden."""
    files: list[Path] = []
    root = paths.root
    for top in INCLUDE_FILES:
        candidate = root / top
        if candidate.exists() and candidate.is_file():
            files.append(candidate)
    for directory in INCLUDE_DIRS:
        base = root / directory
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if not path.is_file():
                continue
            try:
                rel = path.relative_to(root).as_posix()
            except ValueError:
                continue
            if _is_excluded(rel):
                continue
            files.append(path)
    return files


def sanitized_registry_copy(
    source_db: Path,
    target_db: Path,
) -> int:
    """Kopiert die SQLite-DB ohne ``access='private'``- und ``copyright_risk='high'``-Sources.

    Liefert die Anzahl entfernter Source-Reihen. Nutzt ``VACUUM INTO`` fuer einen
    konsistenten Snapshot, dann ``DELETE`` auf der Kopie.
    """
    target_db.parent.mkdir(parents=True, exist_ok=True)
    if target_db.exists():
        target_db.unlink()
    src_conn = connect(source_db)
    try:
        # VACUUM INTO erstellt ein konsistentes File ohne offenen WAL.
        src_conn.execute("VACUUM INTO ?", (str(target_db),))
    finally:
        src_conn.close()

    removed = 0
    dst_conn = sqlite3.connect(str(target_db), isolation_level=None)
    try:
        dst_conn.row_factory = sqlite3.Row
        dst_conn.execute("PRAGMA foreign_keys = OFF")
        # Pro privater Source: lint_findings auf source_id NULLen, page_sources entfernen,
        # claims/source_id NULL ist FK-violation -> nur Page-Sources-Zuordnung loesen,
        # die Quelle selbst loeschen.
        rows = dst_conn.execute(
            "SELECT id FROM sources WHERE access = 'private' OR copyright_risk = 'high'"
        ).fetchall()
        for row in rows:
            sid = row["id"]
            dst_conn.execute("DELETE FROM page_sources WHERE source_id = ?", (sid,))
            dst_conn.execute(
                "UPDATE lint_findings SET source_id = NULL WHERE source_id = ?", (sid,)
            )
            dst_conn.execute("DELETE FROM source_snapshots WHERE source_id = ?", (sid,))
            # claims.source_id ist NOT NULL — wir koennen die Claim nicht behalten,
            # ohne ihre Quellenbindung zu verlieren. Strategie: Claim mitloeschen.
            dst_conn.execute("DELETE FROM claims WHERE source_id = ?", (sid,))
            dst_conn.execute("DELETE FROM ingest_runs WHERE source_id = ?", (sid,))
            dst_conn.execute("DELETE FROM proposals WHERE source_id = ?", (sid,))
            dst_conn.execute("DELETE FROM quarantine_cases WHERE source_id = ?", (sid,))
            dst_conn.execute("DELETE FROM extractions WHERE source_id = ?", (sid,))
            dst_conn.execute("DELETE FROM sources WHERE id = ?", (sid,))
            removed += 1
        dst_conn.execute("PRAGMA foreign_keys = ON")
        dst_conn.execute("VACUUM")
    finally:
        dst_conn.close()
    return removed


def _manifest(
    files: list[tuple[str, Path]],
    *,
    git_sha: str | None,
    sanitized_sources_removed: int,
) -> dict[str, object]:
    file_entries: list[dict[str, object]] = []
    bytes_total = 0
    for arcname, path in files:
        size = path.stat().st_size
        file_entries.append(
            {
                "path": arcname,
                "sha256": _sha256_of(path),
                "bytes": size,
            }
        )
        bytes_total += size
    return {
        "schema_version": BUNDLE_SCHEMA_VERSION,
        "created_at": datetime.now(tz=UTC).isoformat(timespec="seconds"),
        "package_version": __version__,
        "git_sha": git_sha,
        "sanitized_sources_removed": sanitized_sources_removed,
        "files_count": len(file_entries),
        "bytes_total": bytes_total,
        "files": file_entries,
    }


def build_bundle(
    target_zip: Path,
    *,
    paths: VaultPaths | None = None,
    git_sha: str | None = None,
    sanitize_registry: bool = True,
) -> BundleResult:
    """Baut ein Deployment-ZIP nach ``target_zip``.

    - ``paths``: Vault-Wurzel (default: ``get_paths()``).
    - ``git_sha``: optional, wird ins Manifest geschrieben.
    - ``sanitize_registry``: wenn True (Default), wird die SQLite-Kopie um
      ``access='private'``- und ``copyright_risk='high'``-Sources bereinigt.

    Atomic: schreibt nach ``<target>.tmp`` und benennt um.
    """
    paths = paths or get_paths()
    target_zip.parent.mkdir(parents=True, exist_ok=True)
    tmp_zip = target_zip.with_suffix(target_zip.suffix + ".tmp")

    staging = target_zip.parent / f".staging-{target_zip.stem}"
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True)

    try:
        # 1. Files unterhalb der Whitelist sammeln.
        files = _walk_included(paths)

        # 2. SQLite bereinigen.
        sanitized_db = staging / "data" / "registry" / "curiosity.sqlite"
        sanitized_removed = 0
        live_db = paths.registry_db
        if live_db.exists() and sanitize_registry:
            sanitized_removed = sanitized_registry_copy(live_db, sanitized_db)
        elif live_db.exists():
            sanitized_db.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(live_db, sanitized_db)

        # 3. Pfad-Liste zusammensetzen: Whitelist-Files + (ggf.) bereinigte DB.
        zip_files: list[tuple[str, Path]] = []
        for path in files:
            arcname = path.relative_to(paths.root).as_posix()
            zip_files.append((arcname, path))
        if sanitized_db.exists():
            zip_files.append(("data/registry/curiosity.sqlite", sanitized_db))

        # 4. Manifest erzeugen (Hashes berechnen).
        manifest = _manifest(
            zip_files,
            git_sha=git_sha,
            sanitized_sources_removed=sanitized_removed,
        )

        # 5. ZIP schreiben (DEFLATED, Manifest zuerst).
        with zipfile.ZipFile(tmp_zip, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr(
                "manifest.json",
                json.dumps(manifest, ensure_ascii=False, indent=2),
            )
            for arcname, path in zip_files:
                zf.write(path, arcname=arcname)

        # 6. atomarer Rename
        if target_zip.exists():
            target_zip.unlink()
        tmp_zip.replace(target_zip)

        return BundleResult(
            bundle_path=str(target_zip),
            manifest_path="manifest.json",
            files_count=len(zip_files),
            bytes_total=int(manifest["bytes_total"]),
            sanitized_sources_removed=sanitized_removed,
            git_sha=git_sha,
        )
    finally:
        with contextlib.suppress(OSError):
            shutil.rmtree(staging)
        with contextlib.suppress(OSError):
            if tmp_zip.exists():
                tmp_zip.unlink()
