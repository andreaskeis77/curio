"""Proposal-Store: Dateien auf Platte (proposal.yaml, summary.md, risk_notes.md)."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import yaml

from curiosity_wiki.agents.client import RunEvidence
from curiosity_wiki.agents.schemas import IngestProposalV1


def proposal_directory(root: Path, captured_at: datetime, run_id: str) -> Path:
    """Pfad-Schema: ``proposals/<YYYY>/<MM>/<DD>/<run_id>/``."""
    return (
        root
        / "proposals"
        / f"{captured_at.year:04d}"
        / f"{captured_at.month:02d}"
        / f"{captured_at.day:02d}"
        / run_id
    )


def write_proposal(
    *,
    proposal_dir: Path,
    proposal_id: str,
    proposal: IngestProposalV1,
    evidence: RunEvidence,
    source_id: str,
    raw_text_excerpt: str,
) -> None:
    """Schreibt proposal.yaml, summary.md, risk_notes.md, run_evidence.yaml."""
    proposal_dir.mkdir(parents=True, exist_ok=True)

    payload = {
        "proposal_id": proposal_id,
        "source_id": source_id,
        "run_id": evidence.run_id,
        "created_at": evidence.finished_at.isoformat(timespec="seconds"),
        "overall_confidence": proposal.overall_confidence.value,
        "summary": proposal.summary,
        "new_pages_count": len(proposal.new_pages),
        "hard_facts_count": len(proposal.hard_facts),
        "open_questions_count": len(proposal.open_questions),
        "risk_notes_count": len(proposal.risk_notes),
        "data": proposal.model_dump(mode="json"),
    }
    _atomic_write(
        proposal_dir / "proposal.yaml",
        yaml.safe_dump(payload, allow_unicode=True, sort_keys=False),
    )

    summary_lines = [
        f"# Proposal {proposal_id}",
        "",
        f"**Source:** `{source_id}`",
        f"**Run:** `{evidence.run_id}`",
        f"**Confidence:** `{proposal.overall_confidence.value}`",
        "",
        "## Zusammenfassung",
        "",
        proposal.summary or "_(keine Zusammenfassung)_",
        "",
        "## Vorgeschlagene Seiten",
        "",
    ]
    if proposal.new_pages:
        for page in proposal.new_pages:
            summary_lines.append(
                f"- **{page.title}** (`{page.type.value}`, {page.confidence.value})"
            )
            if page.why_interesting:
                summary_lines.append(f"  - {page.why_interesting}")
    else:
        summary_lines.append("_(keine Seiten vorgeschlagen)_")
    summary_lines.extend(
        [
            "",
            "## Harte Fakten",
            "",
        ]
    )
    if proposal.hard_facts:
        for fact in proposal.hard_facts:
            summary_lines.append(
                f"- {fact.claim_text} (`{fact.claim_type}`, {fact.confidence.value})"
            )
    else:
        summary_lines.append("_(keine harten Fakten markiert)_")
    summary_lines.extend(["", "## Offene Fragen", ""])
    if proposal.open_questions:
        for q in proposal.open_questions:
            summary_lines.append(f"- {q}")
    else:
        summary_lines.append("_(keine offenen Fragen)_")
    _atomic_write(proposal_dir / "summary.md", "\n".join(summary_lines) + "\n")

    risk_lines = [f"# Risk Notes — {proposal_id}", ""]
    if proposal.risk_notes:
        for risk in proposal.risk_notes:
            risk_lines.append(f"- **{risk.risk_type.value}** (severity: `{risk.severity.value}`)")
            risk_lines.append(f"  - {risk.description}")
    else:
        risk_lines.append("_(keine Risk Notes)_")
    _atomic_write(proposal_dir / "risk_notes.md", "\n".join(risk_lines) + "\n")

    run_payload = {
        "run_id": evidence.run_id,
        "source_id": evidence.source_id,
        "prompt_id": evidence.prompt_id,
        "prompt_hash": evidence.prompt_hash,
        "provider": evidence.provider,
        "model": evidence.model,
        "temperature": evidence.temperature,
        "started_at": evidence.started_at.isoformat(timespec="seconds"),
        "finished_at": evidence.finished_at.isoformat(timespec="seconds"),
        "status": evidence.status,
        "token_usage": evidence.token_usage,
        "raw_text_excerpt": raw_text_excerpt[:2000],
    }
    _atomic_write(
        proposal_dir / "run_evidence.yaml",
        yaml.safe_dump(run_payload, allow_unicode=True, sort_keys=False),
    )


def write_quarantine_marker(
    *,
    proposal_dir: Path,
    case_type: str,
    severity: str,
    description: str,
    source_id: str,
    run_id: str | None,
) -> None:
    """Schreibt einen Quarantäne-Hinweis als Markdown anstelle eines Proposals."""
    proposal_dir.mkdir(parents=True, exist_ok=True)
    body = (
        f"# Quarantine — {case_type}\n\n"
        f"**Severity:** `{severity}`\n"
        f"**Source:** `{source_id}`\n"
        f"**Run:** `{run_id or 'n/a'}`\n"
        f"**Created:** `{datetime.now(tz=UTC).isoformat(timespec='seconds')}`\n\n"
        f"## Beschreibung\n\n{description}\n"
    )
    _atomic_write(proposal_dir / "QUARANTINE.md", body)


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    tmp.replace(path)
