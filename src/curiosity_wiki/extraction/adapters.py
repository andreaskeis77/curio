"""Format-Adapter für Extraktion (ADR-0011).

Jeder Adapter liefert ``(markdown_text, warnings)`` aus den Roh-Bytes.
Bei Fehler wird ``ExtractionAdapterError`` geworfen — die Pipeline wandelt
das in einen failed-Status um.
"""

from __future__ import annotations

import importlib.metadata
import io
import json
from dataclasses import dataclass

# Maximale Größe der Eingabe (50 MB) — größere Dateien gehen in Quarantäne.
MAX_INPUT_BYTES = 50 * 1024 * 1024


class ExtractionAdapterError(RuntimeError):
    """Adapter-spezifischer Fehler."""


@dataclass(frozen=True)
class AdapterResult:
    """Output eines Format-Adapters."""

    markdown: str
    warnings: list[str]
    extractor: str
    extractor_version: str


def _library_version(name: str) -> str:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return "unknown"


def extract_html(content: bytes) -> AdapterResult:
    """HTML → Markdown mit ``trafilatura`` (favoured_precision)."""
    if len(content) > MAX_INPUT_BYTES:
        raise ExtractionAdapterError(f"HTML input exceeds {MAX_INPUT_BYTES} bytes")

    import trafilatura

    text: str | None
    warnings: list[str] = []
    try:
        text = trafilatura.extract(
            content,
            output_format="markdown",
            include_comments=False,
            include_tables=True,
            favor_precision=True,
        )
    except Exception as exc:
        raise ExtractionAdapterError(f"trafilatura failed: {exc}") from exc

    if not text:
        # Fallback: minimaler Plaintext-Strip
        try:
            decoded = content.decode("utf-8", errors="replace")
        except Exception as exc:
            raise ExtractionAdapterError(f"HTML decode failed: {exc}") from exc
        # primitive Tag-Entfernung
        import re

        stripped = re.sub(r"<[^>]+>", " ", decoded)
        stripped = re.sub(r"\s+", " ", stripped).strip()
        if not stripped:
            raise ExtractionAdapterError("trafilatura returned empty and fallback found no text")
        warnings.append("trafilatura returned empty; used naive plaintext fallback")
        text = stripped

    return AdapterResult(
        markdown=text.strip() + "\n",
        warnings=warnings,
        extractor="trafilatura",
        extractor_version=_library_version("trafilatura"),
    )


def extract_pdf(content: bytes) -> AdapterResult:
    """PDF → Markdown via ``pypdf``. Page-by-Page, mit horizontalen Trennern."""
    if len(content) > MAX_INPUT_BYTES:
        raise ExtractionAdapterError(f"PDF input exceeds {MAX_INPUT_BYTES} bytes")

    from pypdf import PdfReader

    warnings: list[str] = []
    try:
        reader = PdfReader(io.BytesIO(content))
    except Exception as exc:
        raise ExtractionAdapterError(f"pypdf cannot open PDF: {exc}") from exc

    if reader.is_encrypted:
        try:
            reader.decrypt("")
            warnings.append("PDF was encrypted with empty password")
        except Exception as exc:
            raise ExtractionAdapterError(
                f"PDF is encrypted and cannot be decrypted: {exc}"
            ) from exc

    pages: list[str] = []
    for idx, page in enumerate(reader.pages, start=1):
        try:
            text = page.extract_text() or ""
        except Exception as exc:
            warnings.append(f"page {idx} extraction failed: {exc}")
            continue
        text = text.strip()
        if text:
            pages.append(f"## Page {idx}\n\n{text}")
    if not pages:
        raise ExtractionAdapterError("pypdf yielded no extractable text on any page")

    body = "\n\n---\n\n".join(pages) + "\n"
    return AdapterResult(
        markdown=body,
        warnings=warnings,
        extractor="pypdf",
        extractor_version=_library_version("pypdf"),
    )


def extract_markdown(content: bytes) -> AdapterResult:
    """Markdown/Text → Passthrough nach UTF-8-Decode mit BOM-Strip."""
    text = content.decode("utf-8", errors="replace")
    if text.startswith("﻿"):
        text = text.lstrip("﻿")
    text = text.replace("\r\n", "\n")
    if not text.strip():
        raise ExtractionAdapterError("empty text input")
    return AdapterResult(
        markdown=text if text.endswith("\n") else text + "\n",
        warnings=[],
        extractor="passthrough",
        extractor_version="1",
    )


def extract_text(content: bytes) -> AdapterResult:
    """Plaintext → Markdown (mit Code-Block-Wrap, falls binärartig)."""
    text = content.decode("utf-8", errors="replace")
    if text.startswith("﻿"):
        text = text.lstrip("﻿")
    text = text.replace("\r\n", "\n")
    if not text.strip():
        raise ExtractionAdapterError("empty text input")
    return AdapterResult(
        markdown=text if text.endswith("\n") else text + "\n",
        warnings=[],
        extractor="text",
        extractor_version="1",
    )


def extract_data(content: bytes) -> AdapterResult:
    """JSON oder CSV pretty-print, sonst passthrough."""
    text = content.decode("utf-8", errors="replace")
    text = text.replace("\r\n", "\n").strip()
    if not text:
        raise ExtractionAdapterError("empty data input")
    # JSON-Pretty-Print, falls parsbar
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return AdapterResult(
            markdown="```\n" + text + "\n```\n",
            warnings=["non-JSON data; wrapped as code block"],
            extractor="data",
            extractor_version="1",
        )
    pretty = json.dumps(parsed, indent=2, ensure_ascii=False)
    return AdapterResult(
        markdown="```json\n" + pretty + "\n```\n",
        warnings=[],
        extractor="data",
        extractor_version="1",
    )
