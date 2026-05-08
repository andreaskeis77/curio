"""Integrations-Tests für Capture-Adapter (URL/File/Note).

Verwendet einen tmp_vault fixture, der CURIOSITY_VAULT_ROOT überschreibt.
URL-Fetcher wird gemockt — kein realer HTTP-Verkehr.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

from curiosity_wiki.paths import VaultPaths
from curiosity_wiki.registry import connect, migrate
from curiosity_wiki.sources import (
    AccessType,
    CopyrightRisk,
    DuplicateSourceError,
    Reliability,
    Source,
    SourceRepository,
    SourceStatus,
    SourceType,
    capture_file,
    capture_note,
    capture_url,
)
from curiosity_wiki.sources.manifest import read_manifest
from curiosity_wiki.sources.paths import manifest_path


@pytest.fixture
def vault(tmp_path: Path) -> VaultPaths:
    """Schreibbarer Test-Vault mit pyproject-Marker, damit get_vault_root funktioniert."""
    (tmp_path / "pyproject.toml").write_text("[project]\nname='dummy'\n", encoding="utf-8")
    return VaultPaths(root=tmp_path)


@pytest.fixture
def conn(vault: VaultPaths) -> Iterator:
    db_path = vault.registry_db
    with connect(db_path) as connection:
        migrate(connection)
        yield connection


def test_capture_note_creates_source_and_files(vault: VaultPaths, conn) -> None:
    source = capture_note(
        "Pacojet Sorbet Test\nMango war zu süß.",
        why_interesting="Methodenwissen",
        conn=conn,
        paths=vault,
    )
    assert isinstance(source, Source)
    assert source.source_type == SourceType.NOTE
    assert source.access == AccessType.OWN_NOTE
    assert source.reliability == Reliability.PERSONAL
    assert source.status == SourceStatus.CAPTURED
    assert source.title == "Pacojet Sorbet Test"

    # Raw-Datei und Manifest existieren
    raw = vault.root / source.raw_path
    assert raw.exists()
    assert raw.read_bytes().startswith(b"Pacojet Sorbet Test")

    mp = manifest_path(raw.parent)
    assert mp.exists()

    # Registry hat den Eintrag
    repo = SourceRepository(conn)
    fetched = repo.get(source.id)
    assert fetched is not None
    assert fetched.sha256 == source.sha256


def test_manifest_roundtrip(vault: VaultPaths, conn) -> None:
    source = capture_note("Round-trip test", why_interesting="why", conn=conn, paths=vault)
    raw = vault.root / source.raw_path
    mp = manifest_path(raw.parent)
    parsed = read_manifest(mp)
    assert parsed.id == source.id
    assert parsed.sha256 == source.sha256
    assert parsed.access == source.access


def test_duplicate_note_raises(vault: VaultPaths, conn) -> None:
    capture_note("identical content", why_interesting="why", conn=conn, paths=vault)
    with pytest.raises(DuplicateSourceError):
        capture_note("identical content", why_interesting="why again", conn=conn, paths=vault)


def test_duplicate_can_be_forced(vault: VaultPaths, conn) -> None:
    first = capture_note("identical", why_interesting="why", conn=conn, paths=vault)
    second = capture_note(
        "identical",
        why_interesting="forced again",
        conn=conn,
        paths=vault,
        allow_duplicate=True,
    )
    assert second.id != first.id
    assert second.sha256 == first.sha256
    assert SourceRepository(conn).count() == 2


def test_capture_file_copies_and_hashes(vault: VaultPaths, conn, tmp_path: Path) -> None:
    payload = b"hello pdf-like content"
    src_file = tmp_path / "input.pdf"
    src_file.write_bytes(payload)

    source = capture_file(
        src_file,
        why_interesting="reference",
        conn=conn,
        paths=vault,
        source_type=SourceType.PDF,
    )
    assert source.source_type == SourceType.PDF
    assert source.bytes == len(payload)

    raw = vault.root / source.raw_path
    assert raw.exists()
    assert raw.read_bytes() == payload
    # Original-Datei wurde nicht angetastet
    assert src_file.read_bytes() == payload


def test_capture_file_default_access_is_private(vault: VaultPaths, conn, tmp_path: Path) -> None:
    f = tmp_path / "x.bin"
    f.write_bytes(b"content")
    source = capture_file(f, why_interesting="x", conn=conn, paths=vault)
    assert source.access == AccessType.PRIVATE


def test_capture_url_uses_fetcher(vault: VaultPaths, conn) -> None:
    """Mock-Fetcher liefert content; Adapter speichert + persistiert."""
    captured_url = "https://whc.unesco.org/en/list/314"

    def fetcher(url: str) -> tuple[bytes, str | None]:
        assert url == captured_url
        return (b"<html>Alhambra</html>", "text/html; charset=utf-8")

    source = capture_url(
        captured_url,
        why_interesting="UNESCO Pilot Quelle",
        conn=conn,
        paths=vault,
        fetcher=fetcher,
    )
    assert source.source_type == SourceType.WEB
    assert source.original_url == captured_url
    assert source.content_type and "html" in source.content_type
    assert source.reliability == Reliability.OFFICIAL
    assert source.copyright_risk == CopyrightRisk.LOW
    raw = vault.root / source.raw_path
    assert raw.suffix == ".html"
    assert raw.read_bytes() == b"<html>Alhambra</html>"


def test_capture_url_duplicate_url_blocks_second_capture(vault: VaultPaths, conn) -> None:
    url = "https://whc.unesco.org/en/list/100"

    payloads = iter([b"v1", b"v2"])

    def fetcher(_url: str) -> tuple[bytes, str | None]:
        return (next(payloads), "text/html")

    capture_url(url, "first", conn=conn, paths=vault, fetcher=fetcher)
    with pytest.raises(DuplicateSourceError):
        capture_url(url, "second", conn=conn, paths=vault, fetcher=fetcher)


def test_capture_url_overrides_apply(vault: VaultPaths, conn) -> None:
    def fetcher(_url: str) -> tuple[bytes, str | None]:
        return (b"<html>x</html>", "text/html")

    source = capture_url(
        "https://whc.unesco.org/special",
        "why",
        conn=conn,
        paths=vault,
        fetcher=fetcher,
        overrides={"access": "private", "llm_allowed": False},
    )
    assert source.access == AccessType.PRIVATE
    assert source.llm_allowed is False
    # reliability bleibt aus Domain-Regel (override hat sie nicht angefasst)
    assert source.reliability == Reliability.OFFICIAL


def test_empty_note_raises(vault: VaultPaths, conn) -> None:
    from curiosity_wiki.sources import CaptureError

    with pytest.raises(CaptureError):
        capture_note("   ", why_interesting="why", conn=conn, paths=vault)
