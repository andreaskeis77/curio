"""M6 Tests: Bundle-Builder (ADR-0017)."""

from __future__ import annotations

import json
import shutil
import sqlite3
import zipfile
from collections.abc import Iterator
from pathlib import Path

import pytest

from curiosity_wiki.deploy import build_bundle
from curiosity_wiki.paths import VaultPaths, get_paths
from curiosity_wiki.read_models import rebuild_all
from curiosity_wiki.registry import connect, migrate
from curiosity_wiki.sources import capture_note


@pytest.fixture
def vault(tmp_path: Path) -> VaultPaths:
    (tmp_path / "pyproject.toml").write_text("[project]\nname='dummy'\n", encoding="utf-8")
    real = get_paths().prompts
    if real.exists():
        shutil.copytree(real, tmp_path / "prompts")
    real_eval = get_paths().eval
    if real_eval.exists():
        shutil.copytree(real_eval, tmp_path / "eval")
    return VaultPaths(root=tmp_path)


@pytest.fixture
def conn(vault: VaultPaths) -> Iterator:
    with connect(vault.registry_db) as connection:
        migrate(connection)
        yield connection


def test_bundle_zip_created_with_manifest(vault: VaultPaths, conn) -> None:
    target = vault.root / "dist" / "test.zip"
    rebuild_all(conn, paths=vault)
    result = build_bundle(target, paths=vault)
    assert Path(result.bundle_path).exists()
    with zipfile.ZipFile(target) as zf:
        names = zf.namelist()
        assert "manifest.json" in names
        manifest = json.loads(zf.read("manifest.json"))
    assert manifest["schema_version"] == 1
    assert "files" in manifest
    assert manifest["files_count"] == len(manifest["files"])


def test_bundle_includes_wiki_and_read_models(vault: VaultPaths, conn) -> None:
    # Eine Page im wiki-Ordner ablegen, damit rglob etwas findet.
    (vault.wiki / "topics").mkdir(parents=True, exist_ok=True)
    (vault.wiki / "topics" / "demo.md").write_text(
        "---\nid: page_1\ntitle: Demo\nslug: demo\n---\n# Demo", encoding="utf-8"
    )
    rebuild_all(conn, paths=vault)
    target = vault.root / "dist" / "test.zip"
    build_bundle(target, paths=vault)
    with zipfile.ZipFile(target) as zf:
        names = zf.namelist()
    assert any(name == "wiki/topics/demo.md" for name in names)
    assert any(name.startswith("read_models/") for name in names)


def test_bundle_excludes_raw_and_proposals(vault: VaultPaths, conn) -> None:
    (vault.raw).mkdir(parents=True, exist_ok=True)
    (vault.raw / "private.html").write_text("private content", encoding="utf-8")
    (vault.proposals).mkdir(parents=True, exist_ok=True)
    (vault.proposals / "draft.yaml").write_text("draft: true", encoding="utf-8")
    target = vault.root / "dist" / "test.zip"
    build_bundle(target, paths=vault)
    with zipfile.ZipFile(target) as zf:
        names = zf.namelist()
    assert not any(name.startswith("raw/") for name in names)
    assert not any(name.startswith("proposals/") for name in names)


def test_bundle_excludes_dotenv(vault: VaultPaths, conn) -> None:
    (vault.root / ".env").write_text("SECRET=verymuchsecret", encoding="utf-8")
    target = vault.root / "dist" / "test.zip"
    build_bundle(target, paths=vault)
    with zipfile.ZipFile(target) as zf:
        names = zf.namelist()
    assert ".env" not in names
    assert not any(name.endswith("/.env") for name in names)


def test_bundle_sanitizes_private_sources(vault: VaultPaths, conn) -> None:
    """Private Source mit access='private' wird aus der Bundle-DB entfernt."""
    capture_note(
        "Public Note", why_interesting="ok", conn=conn, paths=vault, overrides={"access": "public"}
    )
    capture_note(
        "Private Note",
        why_interesting="ok",
        conn=conn,
        paths=vault,
        overrides={"access": "private"},
    )
    target = vault.root / "dist" / "test.zip"
    result = build_bundle(target, paths=vault, sanitize_registry=True)
    assert result.sanitized_sources_removed >= 1

    # Bundle-DB extrahieren und pruefen.
    with zipfile.ZipFile(target) as zf:
        zf.extractall(vault.root / "extract")
    bundle_db = vault.root / "extract" / "data" / "registry" / "curiosity.sqlite"
    assert bundle_db.exists()
    db = sqlite3.connect(str(bundle_db))
    db.row_factory = sqlite3.Row
    rows = db.execute("SELECT title, access FROM sources").fetchall()
    db.close()
    titles = {row["title"] for row in rows}
    assert "Public Note" in titles
    assert "Private Note" not in titles


def test_bundle_no_sanitize_keeps_private_sources(vault: VaultPaths, conn) -> None:
    """sanitize_registry=False kopiert die DB unbearbeitet (Test-Hilfe)."""
    capture_note(
        "Private Note 2",
        why_interesting="ok",
        conn=conn,
        paths=vault,
        overrides={"access": "private"},
    )
    target = vault.root / "dist" / "test.zip"
    result = build_bundle(target, paths=vault, sanitize_registry=False)
    assert result.sanitized_sources_removed == 0


def test_bundle_manifest_hashes_match_files(vault: VaultPaths, conn) -> None:
    """SHA-256 im Manifest entspricht dem Inhalt im ZIP."""
    import hashlib

    rebuild_all(conn, paths=vault)
    target = vault.root / "dist" / "test.zip"
    build_bundle(target, paths=vault)
    with zipfile.ZipFile(target) as zf:
        manifest = json.loads(zf.read("manifest.json"))
        for entry in manifest["files"]:
            data = zf.read(entry["path"])
            assert hashlib.sha256(data).hexdigest() == entry["sha256"], entry["path"]


def test_bundle_writes_atomic(vault: VaultPaths, conn) -> None:
    """Erfolgsfall: kein .tmp-File haengen geblieben."""
    target = vault.root / "dist" / "test.zip"
    build_bundle(target, paths=vault)
    tmp = target.with_suffix(target.suffix + ".tmp")
    assert not tmp.exists()
    staging = target.parent / f".staging-{target.stem}"
    assert not staging.exists()
