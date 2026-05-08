"""Capture-Adapter: Quellen aus URL, Datei oder Notiz erfassen.

Jeder Adapter:

1. Erzeugt eine ``source_id``.
2. Bestimmt das Zielverzeichnis in ``raw/``.
3. Speichert den Roh-Inhalt unverändert.
4. Berechnet SHA-256.
5. Schreibt Manifest (YAML) und Hash-Beleg.
6. Persistiert die Source in der Registry.

Duplikate (gleiche URL oder gleicher Hash) werfen ``DuplicateSourceError``,
außer ``--allow-duplicate`` bzw. ``allow_duplicate=True`` ist gesetzt.
"""

from __future__ import annotations

import shutil
import sqlite3
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol
from urllib.error import URLError
from urllib.request import Request, urlopen

from curiosity_wiki.ids import generate_source_id
from curiosity_wiki.paths import VaultPaths, get_paths
from curiosity_wiki.sources.hashing import hash_bytes, hash_file
from curiosity_wiki.sources.manifest import write_manifest
from curiosity_wiki.sources.models import (
    AccessType,
    CopyrightRisk,
    Reliability,
    Source,
    SourcePolicy,
    SourceStatus,
    SourceType,
)
from curiosity_wiki.sources.paths import hash_path, manifest_path, source_directory
from curiosity_wiki.sources.policy import guess_source_policy
from curiosity_wiki.sources.repository import SourceRepository

USER_AGENT = "CuriosityWiki/0.1 (+https://github.com/andreaskeis77/curio)"


class CaptureError(RuntimeError):
    """Generischer Capture-Fehler."""


class DuplicateSourceError(CaptureError):
    """Wird geworfen, wenn URL oder Hash bereits in der Registry existieren."""

    def __init__(self, message: str, existing_id: str) -> None:
        super().__init__(message)
        self.existing_id = existing_id


class UrlFetcher(Protocol):
    """Schmale Schnittstelle für URL-Downloads — testbar mockbar."""

    def __call__(self, url: str) -> tuple[bytes, str | None]:
        """Liefert ``(content_bytes, content_type)``."""
        ...


def _default_url_fetcher(url: str) -> tuple[bytes, str | None]:
    """Stdlib-Fetcher mit User-Agent und 30 Sekunden Timeout."""
    req = Request(url, headers={"User-Agent": USER_AGENT})
    if not (url.startswith("http://") or url.startswith("https://")):
        raise CaptureError(f"Only http(s) URLs are supported, got: {url!r}")
    try:
        with urlopen(req, timeout=30) as resp:
            content = resp.read()
            content_type = resp.headers.get("Content-Type")
    except URLError as exc:
        raise CaptureError(f"Failed to fetch {url}: {exc}") from exc
    return content, content_type


def _now() -> datetime:
    return datetime.now(tz=UTC)


def _apply_overrides(policy: SourcePolicy, overrides: dict[str, object]) -> SourcePolicy:
    """Erlaubt CLI-Overrides für Policy-Felder."""
    changes: dict[str, object] = {}
    if "access" in overrides and overrides["access"] is not None:
        changes["access"] = AccessType(str(overrides["access"]))
    if "copyright_risk" in overrides and overrides["copyright_risk"] is not None:
        changes["copyright_risk"] = CopyrightRisk(str(overrides["copyright_risk"]))
    if "reliability" in overrides and overrides["reliability"] is not None:
        changes["reliability"] = Reliability(str(overrides["reliability"]))
    if "llm_allowed" in overrides and overrides["llm_allowed"] is not None:
        changes["llm_allowed"] = bool(overrides["llm_allowed"])
    return replace(policy, **changes) if changes else policy


def _check_duplicates(
    repo: SourceRepository,
    *,
    sha256: str,
    url: str | None,
    allow_duplicate: bool,
) -> None:
    if allow_duplicate:
        return
    existing_by_hash = repo.find_by_hash(sha256)
    if existing_by_hash is not None:
        raise DuplicateSourceError(
            f"Source with sha256={sha256[:12]}... already exists as {existing_by_hash.id}",
            existing_id=existing_by_hash.id,
        )
    if url:
        existing_by_url = repo.find_by_url(url)
        if existing_by_url is not None:
            raise DuplicateSourceError(
                f"Source with url={url!r} already exists as {existing_by_url.id}",
                existing_id=existing_by_url.id,
            )


def _persist(
    *,
    paths: VaultPaths,
    conn: sqlite3.Connection,
    source: Source,
    raw_dir: Path,
) -> Source:
    write_manifest(manifest_path(raw_dir), source)
    hash_path(raw_dir).write_text(source.sha256 + "\n", encoding="utf-8")

    SourceRepository(conn).insert(source)
    return source


def capture_url(
    url: str,
    why_interesting: str,
    *,
    conn: sqlite3.Connection,
    paths: VaultPaths | None = None,
    title: str | None = None,
    fetcher: UrlFetcher | None = None,
    allow_duplicate: bool = False,
    overrides: dict[str, object] | None = None,
) -> Source:
    """Speichert eine Webseite als Source-Snapshot."""
    paths = paths or get_paths()
    fetcher = fetcher or _default_url_fetcher
    overrides = overrides or {}

    content, content_type = fetcher(url)
    sha = hash_bytes(content)

    repo = SourceRepository(conn)
    _check_duplicates(repo, sha256=sha, url=url, allow_duplicate=allow_duplicate)

    captured_at = _now()
    source_id = generate_source_id()
    raw_dir = source_directory(paths, SourceType.WEB, source_id, captured_at)
    raw_dir.mkdir(parents=True, exist_ok=True)

    suffix = ".html" if (content_type and "html" in content_type.lower()) else ".bin"
    raw_file = raw_dir / f"original{suffix}"
    raw_file.write_bytes(content)

    policy = _apply_overrides(guess_source_policy(url), overrides)
    relative_raw = str(raw_file.relative_to(paths.root))
    source = Source(
        id=source_id,
        title=title,
        source_type=SourceType.WEB,
        original_url=url,
        canonical_url=None,
        captured_at=captured_at,
        raw_path=relative_raw,
        extracted_path=None,
        sha256=sha,
        bytes=len(content),
        content_type=content_type,
        language=None,
        access=policy.access,
        copyright_risk=policy.copyright_risk,
        reliability=policy.reliability,
        llm_allowed=policy.llm_allowed,
        status=SourceStatus.CAPTURED,
        why_interesting=why_interesting,
        license_note=policy.license_note,
        created_at=captured_at,
        updated_at=captured_at,
    )
    return _persist(paths=paths, conn=conn, source=source, raw_dir=raw_dir)


def capture_file(
    file_path: Path,
    why_interesting: str,
    *,
    conn: sqlite3.Connection,
    paths: VaultPaths | None = None,
    title: str | None = None,
    source_type: SourceType = SourceType.FILE,
    allow_duplicate: bool = False,
    overrides: dict[str, object] | None = None,
) -> Source:
    """Speichert eine lokale Datei als Source-Snapshot (Kopie nach raw/)."""
    paths = paths or get_paths()
    overrides = overrides or {}

    if not file_path.exists() or not file_path.is_file():
        raise CaptureError(f"File not found or not a file: {file_path}")

    sha = hash_file(file_path)
    size = file_path.stat().st_size

    repo = SourceRepository(conn)
    _check_duplicates(repo, sha256=sha, url=None, allow_duplicate=allow_duplicate)

    captured_at = _now()
    source_id = generate_source_id()
    raw_dir = source_directory(paths, source_type, source_id, captured_at)
    raw_dir.mkdir(parents=True, exist_ok=True)

    raw_file = raw_dir / f"original{file_path.suffix}"
    shutil.copy2(file_path, raw_file)

    # Lokale Dateien sind defaultmäßig private; User kann via overrides öffnen
    policy = _apply_overrides(
        SourcePolicy(
            access=AccessType.PRIVATE,
            copyright_risk=CopyrightRisk.MEDIUM,
            reliability=Reliability.UNKNOWN,
            llm_allowed=True,
        ),
        overrides,
    )

    source = Source(
        id=source_id,
        title=title or file_path.name,
        source_type=source_type,
        original_url=None,
        canonical_url=None,
        captured_at=captured_at,
        raw_path=str(raw_file.relative_to(paths.root)),
        extracted_path=None,
        sha256=sha,
        bytes=size,
        content_type=None,
        language=None,
        access=policy.access,
        copyright_risk=policy.copyright_risk,
        reliability=policy.reliability,
        llm_allowed=policy.llm_allowed,
        status=SourceStatus.CAPTURED,
        why_interesting=why_interesting,
        license_note=policy.license_note,
        created_at=captured_at,
        updated_at=captured_at,
    )
    return _persist(paths=paths, conn=conn, source=source, raw_dir=raw_dir)


def capture_note(
    text: str,
    why_interesting: str,
    *,
    conn: sqlite3.Connection,
    paths: VaultPaths | None = None,
    title: str | None = None,
    allow_duplicate: bool = False,
    overrides: dict[str, object] | None = None,
) -> Source:
    """Speichert eine eigene Notiz als Source."""
    paths = paths or get_paths()
    overrides = overrides or {}

    if not text.strip():
        raise CaptureError("Note text is empty")

    body = text if text.endswith("\n") else text + "\n"
    encoded = body.encode("utf-8")
    sha = hash_bytes(encoded)

    repo = SourceRepository(conn)
    _check_duplicates(repo, sha256=sha, url=None, allow_duplicate=allow_duplicate)

    captured_at = _now()
    source_id = generate_source_id()
    raw_dir = source_directory(paths, SourceType.NOTE, source_id, captured_at)
    raw_dir.mkdir(parents=True, exist_ok=True)

    raw_file = raw_dir / "original.md"
    raw_file.write_bytes(encoded)

    policy = _apply_overrides(
        SourcePolicy(
            access=AccessType.OWN_NOTE,
            copyright_risk=CopyrightRisk.LOW,
            reliability=Reliability.PERSONAL,
            llm_allowed=True,
        ),
        overrides,
    )

    source = Source(
        id=source_id,
        title=title or _derive_note_title(body),
        source_type=SourceType.NOTE,
        original_url=None,
        canonical_url=None,
        captured_at=captured_at,
        raw_path=str(raw_file.relative_to(paths.root)),
        extracted_path=None,
        sha256=sha,
        bytes=len(encoded),
        content_type="text/markdown",
        language=None,
        access=policy.access,
        copyright_risk=policy.copyright_risk,
        reliability=policy.reliability,
        llm_allowed=policy.llm_allowed,
        status=SourceStatus.CAPTURED,
        why_interesting=why_interesting,
        license_note=policy.license_note,
        created_at=captured_at,
        updated_at=captured_at,
    )
    return _persist(paths=paths, conn=conn, source=source, raw_dir=raw_dir)


def _derive_note_title(body: str) -> str:
    """Erste nicht-leere Zeile, gekürzt auf 80 Zeichen."""
    for line in body.splitlines():
        stripped = line.strip().lstrip("#").strip()
        if stripped:
            return stripped[:80]
    return "Untitled note"
