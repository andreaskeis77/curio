"""Ingest-Pipeline: Source → LLM-Proposal → Persistenz.

Schritte:

1. Source und Extraction laden.
2. Prompt-Injection-Heuristik gegen extracted text.
3. LLM-Client-Aufruf (Mock per Default).
4. Pydantic-Validation (passiert im Wrapper).
5. Proposal-Dateien schreiben (atomic).
6. ``proposals``-Tabelle und ``ingest_runs`` befüllen.
7. Bei Injection oder Schema-Drift: Quarantäne, kein Wiki-Schreib.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import yaml
from pydantic import BaseModel

from curiosity_wiki.agents import (
    LLMClient,
    LLMClientError,
    PromptRegistry,
    SchemaValidationError,
    injection_findings,
)
from curiosity_wiki.agents.client import (
    SqliteIngestRunRecorder,
    register_prompt_in_db,
)
from curiosity_wiki.agents.schemas import IngestProposalV1
from curiosity_wiki.config import CuriosityConfig, load_config
from curiosity_wiki.ids import generate_proposal_id
from curiosity_wiki.paths import VaultPaths, get_paths
from curiosity_wiki.proposals.quarantine import QuarantineCase, QuarantineRepository
from curiosity_wiki.proposals.repository import ProposalRecord, ProposalRepository
from curiosity_wiki.proposals.store import (
    proposal_directory,
    write_proposal,
    write_quarantine_marker,
)
from curiosity_wiki.sources.models import SourceStatus
from curiosity_wiki.sources.repository import SourceRepository

DEFAULT_PROMPT_ID = "ingest_v0_1"
DEFAULT_OUTPUT_SCHEMA: type[BaseModel] = IngestProposalV1


class IngestError(RuntimeError):
    """Allgemeiner Ingest-Fehler."""


class QuarantineDetected(IngestError):
    """Wird intern genutzt, wenn die Pre-Checks die Source quarantänen."""


@dataclass
class IngestResult:
    """Ergebnis eines Ingest-Laufs."""

    proposal_id: str | None
    run_id: str | None
    proposal_path: str | None
    status: str
    quarantine_case_id: str | None = None
    error_message: str | None = None
    new_pages_count: int = 0
    hard_facts_count: int = 0
    open_questions_count: int = 0
    confidence: str | None = None


def _now() -> datetime:
    return datetime.now(tz=UTC)


def _build_source_metadata_block(metadata: dict[str, object]) -> str:
    """YAML-Block für den Prompt — fokussiert auf das, was der LLM braucht."""
    safe = {
        k: v
        for k, v in metadata.items()
        if k
        in {
            "id",
            "title",
            "source_type",
            "original_url",
            "language",
            "access",
            "copyright_risk",
            "reliability",
            "why_interesting",
            "captured_at",
        }
    }
    return yaml.safe_dump(safe, allow_unicode=True, sort_keys=False).strip()


def _proposal_record(
    *,
    proposal_id: str,
    proposal: IngestProposalV1,
    source_id: str,
    run_id: str | None,
    relative_path: str,
    status: str,
    risk_level: str,
) -> ProposalRecord:
    return ProposalRecord(
        id=proposal_id,
        proposal_type="ingest",
        source_id=source_id,
        run_id=run_id,
        path=relative_path,
        status=status,
        risk_level=risk_level,
        new_pages_count=len(proposal.new_pages),
        hard_facts_count=len(proposal.hard_facts),
        open_questions_count=len(proposal.open_questions),
        confidence=proposal.overall_confidence.value,
        created_at=_now(),
    )


def _highest_risk(proposal: IngestProposalV1) -> str:
    severities = [r.severity.value for r in proposal.risk_notes]
    if "high" in severities:
        return "high"
    if "medium" in severities:
        return "medium"
    return "low"


def ingest_source(
    source_id: str,
    *,
    conn: sqlite3.Connection,
    paths: VaultPaths | None = None,
    config: CuriosityConfig | None = None,
    prompt_id: str = DEFAULT_PROMPT_ID,
) -> IngestResult:
    """Erzeugt aus einer extrahierten Source ein Proposal."""
    paths = paths or get_paths()
    config = config or load_config()

    source_repo = SourceRepository(conn)
    proposal_repo = ProposalRepository(conn)
    quarantine_repo = QuarantineRepository(conn)

    source = source_repo.get(source_id)
    if source is None:
        raise IngestError(f"Source not found: {source_id}")
    if source.status != SourceStatus.EXTRACTED and source.extracted_path is None:
        raise IngestError(
            f"Source {source_id} not extracted yet (status={source.status.value}). "
            "Run 'curiosity extract <id>' first."
        )

    extracted_path = paths.root / (source.extracted_path or f"extracted/{source.id}.md")
    if not extracted_path.exists():
        raise IngestError(f"Extracted file missing: {extracted_path}")
    extracted_text = extracted_path.read_text(encoding="utf-8")

    # 1) Pre-LLM Injection-Heuristik
    findings = injection_findings(extracted_text)
    if findings:
        case_id = "q_" + generate_proposal_id("inject")
        quarantine_repo.insert(
            QuarantineCase(
                id=case_id,
                case_type="prompt_injection",
                severity="high",
                source_id=source.id,
                status="open",
                created_at=_now(),
                evidence={"findings": [f.__dict__ for f in findings]},
                recommended_action=(
                    "Quelle manuell prüfen. Nicht an LLM übergeben. "
                    "Ggf. nur Link + eigene Notiz übernehmen."
                ),
            )
        )
        # Marker-File im Proposal-Tree, damit es leicht auffindbar ist
        run_id_placeholder = generate_proposal_id("quarantine")
        proposal_dir = proposal_directory(paths.root, _now(), run_id_placeholder)
        write_quarantine_marker(
            proposal_dir=proposal_dir,
            case_type="prompt_injection",
            severity="high",
            description=(
                "Heuristic injection findings detected in extracted content. "
                f"{len(findings)} match(es). LLM call skipped."
            ),
            source_id=source.id,
            run_id=None,
        )
        # Source-Status auf quarantined
        conn.execute(
            "UPDATE sources SET status = ?, updated_at = ? WHERE id = ?",
            (
                SourceStatus.QUARANTINED.value,
                _now().isoformat(timespec="seconds"),
                source.id,
            ),
        )
        return IngestResult(
            proposal_id=None,
            run_id=None,
            proposal_path=str(proposal_dir.relative_to(paths.root)),
            status="quarantined",
            quarantine_case_id=case_id,
            error_message=f"prompt_injection: {len(findings)} finding(s)",
        )

    # 2) Prompt-Registry laden + Run Recorder
    registry = PromptRegistry.from_dir(paths.prompts)
    definition = registry.get(prompt_id)
    register_prompt_in_db(conn, definition)

    recorder = SqliteIngestRunRecorder(conn=conn)
    client = LLMClient(registry=registry, config=config, recorder=recorder)

    # 3) LLM-Call
    metadata_block = _build_source_metadata_block(
        {
            "id": source.id,
            "title": source.title,
            "source_type": source.source_type.value,
            "original_url": source.original_url,
            "language": source.language,
            "access": source.access.value,
            "copyright_risk": source.copyright_risk.value,
            "reliability": source.reliability.value,
            "why_interesting": source.why_interesting,
            "captured_at": source.captured_at.isoformat(timespec="seconds"),
        }
    )
    inputs = {
        "source_metadata": metadata_block,
        "extracted_content": extracted_text,
    }

    try:
        proposal, evidence = client.complete(
            prompt_id=prompt_id,
            source_id=source.id,
            inputs=inputs,
            output_schema=DEFAULT_OUTPUT_SCHEMA,
        )
    except SchemaValidationError as exc:
        case_id = "q_" + generate_proposal_id("schema")
        quarantine_repo.insert(
            QuarantineCase(
                id=case_id,
                case_type="schema_violation",
                severity="medium",
                source_id=source.id,
                status="open",
                created_at=_now(),
                evidence={"error": str(exc)},
                recommended_action="Prompt-Output-Schema prüfen oder Prompt aktualisieren.",
            )
        )
        return IngestResult(
            proposal_id=None,
            run_id=None,
            proposal_path=None,
            status="schema_failed",
            quarantine_case_id=case_id,
            error_message=str(exc),
        )
    except LLMClientError as exc:
        return IngestResult(
            proposal_id=None,
            run_id=None,
            proposal_path=None,
            status="failed",
            error_message=str(exc),
        )

    # 4) Proposal persistieren (Files + DB)
    proposal_id = generate_proposal_id(f"ingest_{source.id[:24]}")
    proposal_dir = proposal_directory(paths.root, _now(), evidence.run_id)
    write_proposal(
        proposal_dir=proposal_dir,
        proposal_id=proposal_id,
        proposal=proposal,
        evidence=evidence,
        source_id=source.id,
        raw_text_excerpt=extracted_text,
    )
    relative_path = str(proposal_dir.relative_to(paths.root))
    risk_level = _highest_risk(proposal)
    record = _proposal_record(
        proposal_id=proposal_id,
        proposal=proposal,
        source_id=source.id,
        run_id=evidence.run_id,
        relative_path=relative_path,
        status="pending",
        risk_level=risk_level,
    )
    proposal_repo.insert(record)

    # ingest_runs.proposal_id ergänzen
    conn.execute(
        "UPDATE ingest_runs SET proposal_id = ? WHERE id = ?",
        (proposal_id, evidence.run_id),
    )

    # Source-Status: classified (= bereit für Review/Publish)
    conn.execute(
        "UPDATE sources SET status = ?, updated_at = ? WHERE id = ?",
        (
            SourceStatus.CLASSIFIED.value,
            _now().isoformat(timespec="seconds"),
            source.id,
        ),
    )

    return IngestResult(
        proposal_id=proposal_id,
        run_id=evidence.run_id,
        proposal_path=relative_path,
        status="pending",
        new_pages_count=record.new_pages_count,
        hard_facts_count=record.hard_facts_count,
        open_questions_count=record.open_questions_count,
        confidence=record.confidence,
    )


# ``Path`` Re-Export für Konsumenten, die Path nicht doppelt importieren wollen
__all__ = [
    "DEFAULT_PROMPT_ID",
    "IngestError",
    "IngestResult",
    "Path",
    "QuarantineDetected",
    "ingest_source",
]
