"""Scout-Runner (M7, ADR-0019).

Volle Pipeline: Lock akquirieren -> Frequenz pruefen -> Sources iterieren ->
capture/extract/ingest -> scout_runs-Eintrag und Markdown-Run-Log schreiben.
Kein Direkt-Schreib nach ``wiki/`` — Update-Proposals durchlaufen weiter den
M3-Review-Workflow.
"""

from __future__ import annotations

import contextlib
import sqlite3
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from curiosity_wiki.config import CuriosityConfig
from curiosity_wiki.extraction import ExtractionError, extract_source
from curiosity_wiki.ids import generate_run_id
from curiosity_wiki.paths import VaultPaths, get_paths
from curiosity_wiki.proposals import IngestError, ingest_source
from curiosity_wiki.scouts.loader import load_scout
from curiosity_wiki.scouts.locks import LockBusyError, acquire_lock, release_lock
from curiosity_wiki.scouts.models import ScoutDefinition, ScoutSource, ScoutSourceType
from curiosity_wiki.sources import (
    CaptureError,
    DuplicateSourceError,
    capture_file,
    capture_note,
    capture_url,
)


@dataclass
class _SourceOutcome:
    """Pro Source: was passierte beim Lauf."""

    label: str
    action: str  # captured | unchanged | quarantined | error | skipped
    proposal_id: str | None = None
    detail: str = ""


@dataclass
class ScoutRunResult:
    """Ergebnis eines Scout-Laufs."""

    run_id: str
    scout_id: str
    status: str
    sources_seen: int = 0
    captured: int = 0
    skipped: int = 0
    proposals: int = 0
    quarantined: int = 0
    errors: int = 0
    log_path: str | None = None
    error_message: str | None = None
    proposal_ids: list[str] = field(default_factory=list)


def _now() -> datetime:
    return datetime.now(tz=UTC)


def _last_run_at(conn: sqlite3.Connection, scout_id: str) -> datetime | None:
    row = conn.execute(
        "SELECT started_at FROM scout_runs "
        "WHERE scout_id = ? AND status IN ('completed', 'skipped') "
        "ORDER BY started_at DESC LIMIT 1",
        (scout_id,),
    ).fetchone()
    if row is None or not row["started_at"]:
        return None
    started = datetime.fromisoformat(str(row["started_at"]))
    if started.tzinfo is None:
        started = started.replace(tzinfo=UTC)
    return started


def _insert_scout_run(
    conn: sqlite3.Connection,
    *,
    run_id: str,
    scout_id: str,
    started_at: datetime,
    status: str,
) -> None:
    conn.execute(
        "INSERT INTO scout_runs (id, scout_id, started_at, status) VALUES (?, ?, ?, ?)",
        (run_id, scout_id, started_at.isoformat(timespec="seconds"), status),
    )


def _update_scout_run(
    conn: sqlite3.Connection,
    *,
    run_id: str,
    finished_at: datetime,
    status: str,
    counts: dict[str, int],
    log_path: str | None,
    error_message: str | None,
) -> None:
    conn.execute(
        """
        UPDATE scout_runs
           SET finished_at = ?, status = ?, sources_seen = ?, captured = ?,
               skipped = ?, proposals = ?, quarantined = ?, errors = ?,
               log_path = ?, error_message = ?
         WHERE id = ?
        """,
        (
            finished_at.isoformat(timespec="seconds"),
            status,
            counts.get("sources_seen", 0),
            counts.get("captured", 0),
            counts.get("skipped", 0),
            counts.get("proposals", 0),
            counts.get("quarantined", 0),
            counts.get("errors", 0),
            log_path,
            error_message,
            run_id,
        ),
    )


def _capture_for_source(
    source: ScoutSource,
    *,
    conn: sqlite3.Connection,
    paths: VaultPaths,
    llm_allowed: bool,
):
    overrides: dict[str, object] = {"llm_allowed": llm_allowed}
    if source.type == ScoutSourceType.URL:
        return capture_url(
            source.value,
            why_interesting=source.why_interesting or "scout-update",
            conn=conn,
            paths=paths,
            title=source.title,
            allow_duplicate=False,
            overrides=overrides,
        )
    if source.type == ScoutSourceType.NOTE:
        return capture_note(
            source.value,
            why_interesting=source.why_interesting or "scout-update",
            conn=conn,
            paths=paths,
            title=source.title,
            allow_duplicate=False,
            overrides=overrides,
        )
    if source.type == ScoutSourceType.FILE:
        return capture_file(
            Path(source.value),
            why_interesting=source.why_interesting or "scout-update",
            conn=conn,
            paths=paths,
            title=source.title,
            allow_duplicate=False,
            overrides=overrides,
        )
    raise ValueError(f"unsupported scout source type: {source.type}")


def _label_for(source: ScoutSource) -> str:
    if source.title:
        return source.title
    if source.type == ScoutSourceType.NOTE:
        first_line = (
            source.value.strip().splitlines()[0] if source.value.strip() else "(empty note)"
        )
        return f"note: {first_line[:60]}"
    return f"{source.type.value}: {source.value[:80]}"


def _write_run_log(
    paths: VaultPaths,
    *,
    run_id: str,
    scout: ScoutDefinition,
    started_at: datetime,
    finished_at: datetime,
    status: str,
    counts: dict[str, int],
    outcomes: list[_SourceOutcome],
    error_message: str | None,
) -> str:
    target_dir = paths.ops_logs / "scout_runs"
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"{run_id}.md"
    lines = [
        f"# Scout Run {run_id}",
        "",
        f"**Scout:** {scout.id}",
        f"**Domain:** {scout.domain}",
        f"**Started:** {started_at.isoformat(timespec='seconds')}",
        f"**Finished:** {finished_at.isoformat(timespec='seconds')}",
        f"**Status:** {status}",
        "",
        "## Counts",
        "",
        "| metric | value |",
        "| --- | --- |",
    ]
    for key in ("sources_seen", "captured", "skipped", "proposals", "quarantined", "errors"):
        lines.append(f"| {key} | {counts.get(key, 0)} |")
    if error_message:
        lines.extend(["", "## Error", "", f"`{error_message}`"])
    lines.extend(
        [
            "",
            "## Sources",
            "",
            "| source | action | proposal | detail |",
            "| --- | --- | --- | --- |",
        ]
    )
    for outcome in outcomes:
        lines.append(
            f"| {outcome.label} | {outcome.action} | {outcome.proposal_id or '—'} | {outcome.detail or '—'} |"
        )
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return str(target.relative_to(paths.root))


def run_scout(
    scout_id: str,
    *,
    conn: sqlite3.Connection,
    paths: VaultPaths | None = None,
    config: CuriosityConfig | None = None,
    force: bool = False,
    dry_run: bool | None = None,
) -> ScoutRunResult:
    """Top-Level-Funktion fuer einen Scout-Run.

    - ``force=True`` ueberschreibt die ``frequency_hours``-Schranke.
    - ``dry_run`` setzt den Lauf in den No-Op-Modus (kein Capture, kein Ingest).
      Default: aus der YAML uebernehmen.
    """
    paths = paths or get_paths()
    scout = load_scout(scout_id, paths=paths)
    effective_dry_run = bool(scout.limits.dry_run if dry_run is None else dry_run)

    started_at = _now()
    run_id = "sr_" + generate_run_id()
    lock_path = paths.root / "data" / "scout_locks" / f"{scout.id}.lock"

    # 1. Lock
    try:
        acquire_lock(lock_path)
    except LockBusyError as exc:
        return ScoutRunResult(
            run_id=run_id, scout_id=scout.id, status="skipped", error_message=str(exc)
        )

    counts = {
        "sources_seen": 0,
        "captured": 0,
        "skipped": 0,
        "proposals": 0,
        "quarantined": 0,
        "errors": 0,
    }
    outcomes: list[_SourceOutcome] = []
    proposal_ids: list[str] = []
    status = "running"
    error_message: str | None = None

    log_path: str | None = None
    skipped_run = False

    try:
        # Insert sofort — Update auf finalen Status erfolgt im finally-Block.
        _insert_scout_run(
            conn,
            run_id=run_id,
            scout_id=scout.id,
            started_at=started_at,
            status="running",
        )

        # 2. Frequenz-Check (last_run_at filtert auf completed/skipped; der gerade
        # eingefuegte running-Eintrag wird also korrekterweise ignoriert).
        last_run = _last_run_at(conn, scout.id)
        if not force and last_run is not None:
            elapsed = (started_at - last_run).total_seconds() / 3600.0
            if elapsed < scout.frequency_hours:
                detail = (
                    f"only {elapsed:.1f}h since last run; frequency_hours={scout.frequency_hours}"
                )
                outcomes.append(_SourceOutcome(label="(scout)", action="skipped", detail=detail))
                error_message = detail
                status = "skipped"
                skipped_run = True

        # 3. Sources iterieren (nur wenn nicht skipped)
        if not skipped_run:
            sources = list(scout.sources)[: scout.limits.max_sources_per_run]
            for source in sources:
                counts["sources_seen"] += 1
                label = _label_for(source)
                if effective_dry_run:
                    outcomes.append(_SourceOutcome(label=label, action="skipped", detail="dry_run"))
                    counts["skipped"] += 1
                    continue
                try:
                    captured = _capture_for_source(
                        source, conn=conn, paths=paths, llm_allowed=scout.limits.llm_allowed
                    )
                except DuplicateSourceError as exc:
                    outcomes.append(
                        _SourceOutcome(label=label, action="unchanged", detail=str(exc))
                    )
                    counts["skipped"] += 1
                    continue
                except CaptureError as exc:
                    outcomes.append(_SourceOutcome(label=label, action="error", detail=str(exc)))
                    counts["errors"] += 1
                    continue
                counts["captured"] += 1

                try:
                    extract_source(captured.id, conn=conn, paths=paths)
                except ExtractionError as exc:
                    outcomes.append(
                        _SourceOutcome(label=label, action="error", detail=f"extract: {exc}")
                    )
                    counts["errors"] += 1
                    continue

                try:
                    ingest_result = ingest_source(
                        captured.id,
                        conn=conn,
                        paths=paths,
                        config=config,
                        prompt_id=scout.prompt_id,
                    )
                except IngestError as exc:
                    outcomes.append(
                        _SourceOutcome(label=label, action="error", detail=f"ingest: {exc}")
                    )
                    counts["errors"] += 1
                    continue

                if ingest_result.status == "quarantined":
                    outcomes.append(
                        _SourceOutcome(
                            label=label,
                            action="quarantined",
                            detail=ingest_result.error_message or "quarantined",
                        )
                    )
                    counts["quarantined"] += 1
                    continue
                if ingest_result.proposal_id:
                    outcomes.append(
                        _SourceOutcome(
                            label=label,
                            action="captured",
                            proposal_id=ingest_result.proposal_id,
                        )
                    )
                    proposal_ids.append(ingest_result.proposal_id)
                    counts["proposals"] += 1
                else:
                    outcomes.append(
                        _SourceOutcome(
                            label=label,
                            action="error",
                            detail=ingest_result.error_message or "no proposal",
                        )
                    )
                    counts["errors"] += 1

            status = "completed"

    except Exception as exc:  # pragma: no cover - safety net
        status = "failed"
        error_message = f"{exc.__class__.__name__}: {exc}"
    finally:
        finished_at = _now()
        try:
            log_path = _write_run_log(
                paths,
                run_id=run_id,
                scout=scout,
                started_at=started_at,
                finished_at=finished_at,
                status=status,
                counts=counts,
                outcomes=outcomes,
                error_message=error_message,
            )
        except Exception:  # pragma: no cover
            log_path = None
        with contextlib.suppress(sqlite3.Error):  # pragma: no cover
            _update_scout_run(
                conn,
                run_id=run_id,
                finished_at=finished_at,
                status=status,
                counts=counts,
                log_path=log_path,
                error_message=error_message,
            )
        release_lock(lock_path)

    return ScoutRunResult(
        run_id=run_id,
        scout_id=scout.id,
        status=status,
        sources_seen=counts["sources_seen"],
        captured=counts["captured"],
        skipped=counts["skipped"],
        proposals=counts["proposals"],
        quarantined=counts["quarantined"],
        errors=counts["errors"],
        log_path=log_path,
        error_message=error_message,
        proposal_ids=proposal_ids,
    )
