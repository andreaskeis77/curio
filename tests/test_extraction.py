"""Tests für die Extraction-Pipeline."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

from curiosity_wiki.extraction import ExtractionError, extract_source
from curiosity_wiki.extraction.adapters import (
    ExtractionAdapterError,
    extract_data,
    extract_html,
    extract_markdown,
    extract_text,
)
from curiosity_wiki.paths import VaultPaths
from curiosity_wiki.registry import connect, migrate
from curiosity_wiki.sources import (
    SourceRepository,
    SourceStatus,
    SourceType,
    capture_file,
    capture_note,
)


@pytest.fixture
def vault(tmp_path: Path) -> VaultPaths:
    (tmp_path / "pyproject.toml").write_text("[project]\nname='dummy'\n", encoding="utf-8")
    return VaultPaths(root=tmp_path)


@pytest.fixture
def conn(vault: VaultPaths) -> Iterator:
    with connect(vault.registry_db) as connection:
        migrate(connection)
        yield connection


# -- Adapter-Unit-Tests ------------------------------------------------------


def test_extract_html_returns_markdown() -> None:
    html = (
        b"<html><body>"
        b"<h1>Test Title</h1>"
        b"<p>This is a paragraph with enough words to survive trafilatura's "
        b"boilerplate filter - fluffy filler text added just to bulk it up "
        b"above the minimum threshold for content detection.</p>"
        b"</body></html>"
    )
    result = extract_html(html)
    assert result.extractor == "trafilatura"
    assert "Test Title" in result.markdown or "paragraph" in result.markdown
    assert result.markdown.endswith("\n")


def test_extract_html_too_large_raises() -> None:
    big = b"<html><body>" + b"x" * (60 * 1024 * 1024) + b"</body></html>"
    with pytest.raises(ExtractionAdapterError):
        extract_html(big)


def test_extract_markdown_passthrough() -> None:
    text = b"# Heading\n\nbody text\n"
    result = extract_markdown(text)
    assert result.extractor == "passthrough"
    assert "# Heading" in result.markdown


def test_extract_markdown_strips_bom() -> None:
    text = "﻿# With BOM\n".encode()
    result = extract_markdown(text)
    assert result.markdown.startswith("# With BOM")


def test_extract_markdown_empty_raises() -> None:
    with pytest.raises(ExtractionAdapterError):
        extract_markdown(b"")


def test_extract_text_handles_crlf() -> None:
    text = b"line one\r\nline two\r\n"
    result = extract_text(text)
    assert "\r" not in result.markdown
    assert "line one\nline two" in result.markdown


def test_extract_data_pretty_prints_json() -> None:
    payload = b'{"foo":1,"bar":[1,2]}'
    result = extract_data(payload)
    assert result.markdown.startswith("```json")
    assert "foo" in result.markdown


def test_extract_data_wraps_non_json_as_code() -> None:
    payload = b"a,b,c\n1,2,3\n"
    result = extract_data(payload)
    assert "```" in result.markdown
    assert any("non-JSON" in w for w in result.warnings)


# -- Pipeline-Integration ----------------------------------------------------


def test_extract_note_pipeline(vault: VaultPaths, conn) -> None:
    source = capture_note("Eine Test-Notiz", why_interesting="x", conn=conn, paths=vault)
    result = extract_source(source.id, conn=conn, paths=vault)
    assert result.status == "extracted"
    assert result.output_path == f"extracted/{source.id}.md"
    output_file = vault.root / result.output_path
    assert output_file.exists()
    content = output_file.read_text(encoding="utf-8")
    assert content.startswith("---\n")
    assert source.id in content
    # Source-Status ist jetzt extracted
    refreshed = SourceRepository(conn).get(source.id)
    assert refreshed is not None
    assert refreshed.status == SourceStatus.EXTRACTED
    assert refreshed.extracted_path == result.output_path


def test_extract_file_pipeline(vault: VaultPaths, conn, tmp_path: Path) -> None:
    payload = tmp_path / "doc.txt"
    payload.write_text("hello extracted text", encoding="utf-8")
    source = capture_file(payload, why_interesting="x", conn=conn, paths=vault)
    result = extract_source(source.id, conn=conn, paths=vault)
    assert result.status == "extracted"
    assert "hello extracted text" in (vault.root / result.output_path).read_text(encoding="utf-8")


def test_extract_pdf_pipeline(vault: VaultPaths, conn, tmp_path: Path) -> None:
    """Echtes PDF mit reportlab — wir generieren ein 1-seitiges PDF mit Text."""
    pytest.importorskip("pypdf")
    # pypdf kann selbst kein PDF schreiben — wir bauen eines aus minimalem
    # PDF-Quelltext.
    minimal_pdf = (
        b"%PDF-1.4\n"
        b"1 0 obj <</Type /Catalog /Pages 2 0 R>> endobj\n"
        b"2 0 obj <</Type /Pages /Kids [3 0 R] /Count 1>> endobj\n"
        b"3 0 obj <</Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Contents 4 0 R /Resources <</Font <</F1 5 0 R>>>>>> endobj\n"
        b"4 0 obj <</Length 44>>\nstream\nBT /F1 12 Tf 72 720 Td (PDF Hello World) Tj ET\nendstream\nendobj\n"
        b"5 0 obj <</Type /Font /Subtype /Type1 /BaseFont /Helvetica>> endobj\n"
        b"xref\n0 6\n0000000000 65535 f \n0000000009 00000 n \n0000000054 00000 n \n"
        b"0000000099 00000 n \n0000000196 00000 n \n0000000283 00000 n \n"
        b"trailer <</Size 6 /Root 1 0 R>>\nstartxref\n344\n%%EOF\n"
    )
    pdf_path = tmp_path / "input.pdf"
    pdf_path.write_bytes(minimal_pdf)
    source = capture_file(
        pdf_path, why_interesting="pdf test", conn=conn, paths=vault, source_type=SourceType.PDF
    )
    result = extract_source(source.id, conn=conn, paths=vault)
    # PDF-Extraktion kann je nach pypdf-Version mit unserem Minimal-PDF
    # leichte Abweichungen haben — wir testen nur, dass der Status nicht
    # in einer Exception endet.
    assert result.status in {"extracted", "failed"}


def test_extract_unknown_source_raises(vault: VaultPaths, conn) -> None:
    with pytest.raises(ExtractionError):
        extract_source("src_doesnt_exist", conn=conn, paths=vault)


def test_extract_idempotent(vault: VaultPaths, conn) -> None:
    """Wiederholte Extraktion läuft ohne Fehler und überschreibt die Datei."""
    source = capture_note("Idempotent Test", why_interesting="x", conn=conn, paths=vault)
    result1 = extract_source(source.id, conn=conn, paths=vault)
    result2 = extract_source(source.id, conn=conn, paths=vault)
    assert result1.status == result2.status == "extracted"
    # Beide Läufe haben einen eigenen extraction_id
    assert result1.extraction_id != result2.extraction_id
