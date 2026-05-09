"""Extraction-Pipeline.

Liest die Raw-Datei einer Source, wählt den passenden Adapter (ADR-0011),
schreibt ``extracted/<source_id>.md`` atomic, persistiert eine
``extractions``-Zeile und aktualisiert ``sources.status``.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from curiosity_wiki.extraction.adapters import (
    AdapterResult,
    ExtractionAdapterError,
    extract_data,
    extract_html,
    extract_markdown,
    extract_pdf,
    extract_text,
)
from curiosity_wiki.extraction.repository import ExtractionRepository
from curiosity_wiki.ids import generate_run_id
from curiosity_wiki.paths import VaultPaths, get_paths
from curiosity_wiki.sources.hashing import hash_bytes
from curiosity_wiki.sources.models import SourceStatus, SourceType
from curiosity_wiki.sources.repository import SourceRepository


class ExtractionError(RuntimeError):
    """Wird geworfen, wenn die Extraktion endgültig fehlschlägt."""


@dataclass
class ExtractionResult:
    """Zusammenfassung eines Extraction-Laufs."""

    extraction_id: str
    source_id: str
    extractor: str
    extractor_version: str
    output_path: str | None
    output_chars: int | None
    status: str
    warnings: list[str]
    error_message: str | None


def _now() -> datetime:
    return datetime.now(tz=UTC)


def _select_adapter(source_type: SourceType, content: bytes):
    """Adapter-Wahl basierend auf SourceType."""
    if source_type == SourceType.WEB:
        return extract_html(content)
    if source_type == SourceType.PDF:
        return extract_pdf(content)
    if source_type == SourceType.NOTE:
        return extract_markdown(content)
    if source_type == SourceType.DATA:
        return extract_data(content)
    if source_type == SourceType.SCREENSHOT:
        raise ExtractionAdapterError("screenshot extraction not supported (OCR is Phase B)")
    # FILE und alles andere: Text-Versuch
    return extract_text(content)


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def _build_output(source_id: str, adapter_result: AdapterResult, input_sha256: str) -> str:
    """Frontmatter + Body."""
    import yaml

    front = {
        "source_id": source_id,
        "extractor": adapter_result.extractor,
        "extractor_version": adapter_result.extractor_version,
        "extracted_at": _now().isoformat(timespec="seconds"),
        "input_sha256": input_sha256,
        "warnings": adapter_result.warnings,
    }
    yaml_block = yaml.safe_dump(front, allow_unicode=True, sort_keys=False).strip()
    return f"---\n{yaml_block}\n---\n\n{adapter_result.markdown}"


def extract_source(
    source_id: str,
    *,
    conn: sqlite3.Connection,
    paths: VaultPaths | None = None,
) -> ExtractionResult:
    """Extrahiert die Source mit gegebener ID. Persistiert Result und Status.

    Wirft ``ExtractionError``, wenn die Source nicht existiert oder die Raw-Datei
    fehlt; bei Adapter-Fehlern wird das Result mit ``status='failed'`` zurückgegeben
    und keine Exception geworfen — der Aufrufer kann re-runnen.
    """
    paths = paths or get_paths()
    source_repo = SourceRepository(conn)
    extraction_repo = ExtractionRepository(conn)

    source = source_repo.get(source_id)
    if source is None:
        raise ExtractionError(f"Source not found: {source_id}")

    raw_file = paths.root / source.raw_path
    if not raw_file.exists():
        raise ExtractionError(f"Raw file missing: {raw_file}")

    content = raw_file.read_bytes()
    input_sha = hash_bytes(content)

    extraction_id = "ext_" + generate_run_id()
    started_at = _now()

    try:
        adapter_result = _select_adapter(source.source_type, content)
    except ExtractionAdapterError as exc:
        finished_at = _now()
        extraction_repo.insert(
            extraction_id=extraction_id,
            source_id=source.id,
            extractor=source.source_type.value,
            extractor_version="n/a",
            input_sha256=input_sha,
            output_path=None,
            output_sha256=None,
            output_chars=None,
            status="failed",
            started_at=started_at,
            finished_at=finished_at,
            warnings_json=None,
            error_message=str(exc),
        )
        extraction_repo.update_source_status(source.id, SourceStatus.FAILED.value)
        return ExtractionResult(
            extraction_id=extraction_id,
            source_id=source.id,
            extractor=source.source_type.value,
            extractor_version="n/a",
            output_path=None,
            output_chars=None,
            status="failed",
            warnings=[],
            error_message=str(exc),
        )

    output_text = _build_output(source.id, adapter_result, input_sha)
    output_relative = f"extracted/{source.id}.md"
    output_abs = paths.root / output_relative
    _atomic_write_text(output_abs, output_text)

    output_bytes = output_text.encode("utf-8")
    output_sha = hash_bytes(output_bytes)
    finished_at = _now()

    extraction_repo.insert(
        extraction_id=extraction_id,
        source_id=source.id,
        extractor=adapter_result.extractor,
        extractor_version=adapter_result.extractor_version,
        input_sha256=input_sha,
        output_path=output_relative,
        output_sha256=output_sha,
        output_chars=len(adapter_result.markdown),
        status="extracted",
        started_at=started_at,
        finished_at=finished_at,
        warnings_json=json.dumps(adapter_result.warnings) if adapter_result.warnings else None,
        error_message=None,
    )
    # extracted_path und status auf der Source aktualisieren
    conn.execute(
        "UPDATE sources SET extracted_path = ?, status = ?, updated_at = ? WHERE id = ?",
        (
            output_relative,
            SourceStatus.EXTRACTED.value,
            _now().isoformat(timespec="seconds"),
            source.id,
        ),
    )

    return ExtractionResult(
        extraction_id=extraction_id,
        source_id=source.id,
        extractor=adapter_result.extractor,
        extractor_version=adapter_result.extractor_version,
        output_path=output_relative,
        output_chars=len(adapter_result.markdown),
        status="extracted",
        warnings=adapter_result.warnings,
        error_message=None,
    )
