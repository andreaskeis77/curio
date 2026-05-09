"""Curiosity Wiki CLI.

T0.1-Skelett + M1-Befehle.
"""

from __future__ import annotations

import sys
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from curiosity_wiki import __version__
from curiosity_wiki.config import load_config
from curiosity_wiki.extraction import ExtractionError, extract_source
from curiosity_wiki.linting import (
    LintSeverity,
    run_lint,
    write_report_markdown,
)
from curiosity_wiki.paths import VaultPaths, get_paths
from curiosity_wiki.proposals import (
    IngestError,
    ProposalRepository,
    QuarantineRepository,
    ingest_source,
)
from curiosity_wiki.registry import (
    check_schema as registry_check_schema,
)
from curiosity_wiki.registry import (
    connect as registry_connect,
)
from curiosity_wiki.registry import (
    current_schema_version,
    migrate,
)
from curiosity_wiki.sources import (
    CaptureError,
    DuplicateSourceError,
    SourceRepository,
    SourceStatus,
    capture_file,
    capture_note,
    capture_url,
)
from curiosity_wiki.wiki import (
    PageRepository,
    PublishError,
    SlugCollisionError,
    publish_proposal,
    reject_proposal,
    request_changes,
)

console = Console()


@click.group(
    help=(
        "Curiosity Wiki — persönliches, quellengestütztes Wissenssystem.\n\n"
        "Aktuelle Phase: M3 Review & Publish. "
        "M1+M2 plus proposal approve/reject/request-changes, pages list, lint."
    )
)
@click.version_option(version=__version__, prog_name="curiosity")
def cli() -> None:
    """Top-Level-Group."""


# --- Top-Level: paths / info / quality-gates --------------------------------


@cli.command()
def paths() -> None:
    """Zeigt die erkannten Vault-Pfade."""
    p = get_paths()
    table = Table(title="Curiosity Vault Paths", show_lines=False)
    table.add_column("Name", style="bold")
    table.add_column("Path")
    table.add_column("Exists?", justify="right")
    for name, path in p.all_named().items():
        exists = "yes" if path.exists() else "no"
        table.add_row(name, str(path), exists)
    console.print(table)


@cli.command()
def info() -> None:
    """Zeigt Version, Config und Status."""
    cfg = load_config()
    p = get_paths()

    schema_version = 0
    source_count = 0
    if p.registry_db.exists():
        with registry_connect(p.registry_db) as conn:
            schema_version = current_schema_version(conn)
            try:
                source_count = SourceRepository(conn).count()
            except Exception:
                source_count = 0

    table = Table(title=f"Curiosity Wiki v{__version__}", show_lines=False)
    table.add_column("Setting", style="bold")
    table.add_column("Value")
    table.add_row("version", __version__)
    table.add_row("llm_provider", cfg.llm_provider)
    table.add_row("llm_model", cfg.llm_model or "(default)")
    table.add_row("log_level", cfg.log_level)
    table.add_row("dev_fail_fast", str(cfg.dev_fail_fast))
    table.add_row("agent_dry_run", str(cfg.agent_dry_run))
    table.add_row("registry_db", str(p.registry_db))
    table.add_row("registry_exists", "yes" if p.registry_db.exists() else "no")
    table.add_row("schema_version", str(schema_version))
    table.add_row("sources_count", str(source_count))
    console.print(table)
    console.print(
        "\n[dim]Phase: M3 — Review & Publish. See docs/PROJECT_STATE.md for current state.[/dim]"
    )


@cli.command(name="quality-gates")
def quality_gates() -> None:
    """Verweist auf ``tools/run_quality_gates.py``."""
    console.print("Quality Gates run via: [bold]python tools/run_quality_gates.py[/bold]")


# --- Registry-Subgruppe -----------------------------------------------------


@cli.group()
def registry() -> None:
    """Registry-Verwaltung (SQLite)."""


@registry.command(name="init")
def registry_init() -> None:
    """Erstellt/aktualisiert die Registry-Datenbank."""
    p = get_paths()
    with registry_connect(p.registry_db) as conn:
        applied = migrate(conn)
        version = current_schema_version(conn)
    if applied:
        console.print(
            f"[green]Registry up to date.[/green] Applied migrations: "
            f"{', '.join(f'{v:04d}' for v in applied)}. Schema version: {version}"
        )
    else:
        console.print(f"[green]Registry already up to date.[/green] Schema version: {version}")


@registry.command(name="check")
def registry_check() -> None:
    """Prüft Schema-Integrität (Validation Stage 3)."""
    p = get_paths()
    if not p.registry_db.exists():
        console.print(
            "[red]Registry database does not exist.[/red] Run "
            "[bold]curiosity registry init[/bold] first."
        )
        raise SystemExit(1)
    with registry_connect(p.registry_db) as conn:
        ok, findings = registry_check_schema(conn)
        version = current_schema_version(conn)
        source_count = SourceRepository(conn).count()
    if ok:
        console.print(
            f"[green]Registry OK.[/green] Schema version: {version}, sources: {source_count}"
        )
        return
    console.print(f"[red]Registry has issues. Schema version: {version}[/red]")
    for finding in findings:
        console.print(f"  - {finding}")
    raise SystemExit(1)


# --- Capture-Subgruppe ------------------------------------------------------


def _ensure_registry_ready(p: VaultPaths) -> None:
    """Stellt sicher, dass das Schema initialisiert ist (idempotent)."""
    with registry_connect(p.registry_db) as conn:
        migrate(conn)


@cli.group()
def capture() -> None:
    """Quellen erfassen (URL, Datei, Notiz)."""


_OVERRIDE_OPTIONS = [
    click.option("--access", default=None, help="public|private|paywalled|own_note"),
    click.option("--copyright-risk", "copyright_risk", default=None, help="low|medium|high"),
    click.option(
        "--reliability",
        default=None,
        help="official|expert|journalistic|commercial|personal|unknown",
    ),
    click.option(
        "--llm-allowed/--no-llm-allowed",
        "llm_allowed",
        default=None,
        help="Override: darf der LLM-Ingest die Quelle als Volltext nutzen?",
    ),
    click.option(
        "--allow-duplicate",
        is_flag=True,
        default=False,
        help="Erlaubt das Erfassen, auch wenn URL/Hash bereits existiert.",
    ),
    click.option("--why", "why_interesting", required=True, help="Warum interessant?"),
    click.option("--title", default=None, help="Optionaler Titel."),
]


def _apply_options(func):
    for option in reversed(_OVERRIDE_OPTIONS):
        func = option(func)
    return func


def _build_overrides(
    access: str | None,
    copyright_risk: str | None,
    reliability: str | None,
    llm_allowed: bool | None,
) -> dict[str, object]:
    overrides: dict[str, object] = {}
    if access is not None:
        overrides["access"] = access
    if copyright_risk is not None:
        overrides["copyright_risk"] = copyright_risk
    if reliability is not None:
        overrides["reliability"] = reliability
    if llm_allowed is not None:
        overrides["llm_allowed"] = llm_allowed
    return overrides


def _print_source_summary(source) -> None:
    table = Table(title=f"Captured: {source.id}", show_lines=False)
    table.add_column("Field", style="bold")
    table.add_column("Value")
    table.add_row("title", str(source.title))
    table.add_row("type", source.source_type.value)
    table.add_row("url", source.original_url or "")
    table.add_row("raw_path", source.raw_path)
    table.add_row("sha256", source.sha256)
    table.add_row("access", source.access.value)
    table.add_row("copyright_risk", source.copyright_risk.value)
    table.add_row("reliability", source.reliability.value)
    table.add_row("llm_allowed", str(source.llm_allowed))
    table.add_row("status", source.status.value)
    table.add_row("why_interesting", source.why_interesting)
    console.print(table)


@capture.command(name="url")
@click.argument("url")
@_apply_options
def capture_url_cmd(
    url: str,
    why_interesting: str,
    title: str | None,
    access: str | None,
    copyright_risk: str | None,
    reliability: str | None,
    llm_allowed: bool | None,
    allow_duplicate: bool,
) -> None:
    """Erfasst eine URL als Source-Snapshot."""
    p = get_paths()
    _ensure_registry_ready(p)
    overrides = _build_overrides(access, copyright_risk, reliability, llm_allowed)
    try:
        with registry_connect(p.registry_db) as conn:
            source = capture_url(
                url,
                why_interesting,
                conn=conn,
                paths=p,
                title=title,
                allow_duplicate=allow_duplicate,
                overrides=overrides,
            )
    except DuplicateSourceError as exc:
        console.print(f"[yellow]Duplicate detected:[/yellow] {exc}")
        console.print("Use [bold]--allow-duplicate[/bold] to capture anyway.")
        raise SystemExit(2) from None
    except CaptureError as exc:
        console.print(f"[red]Capture failed:[/red] {exc}")
        raise SystemExit(1) from None
    _print_source_summary(source)


@capture.command(name="file")
@click.argument("file_path", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@_apply_options
def capture_file_cmd(
    file_path: Path,
    why_interesting: str,
    title: str | None,
    access: str | None,
    copyright_risk: str | None,
    reliability: str | None,
    llm_allowed: bool | None,
    allow_duplicate: bool,
) -> None:
    """Erfasst eine lokale Datei als Source."""
    p = get_paths()
    _ensure_registry_ready(p)
    overrides = _build_overrides(access, copyright_risk, reliability, llm_allowed)
    try:
        with registry_connect(p.registry_db) as conn:
            source = capture_file(
                file_path,
                why_interesting,
                conn=conn,
                paths=p,
                title=title,
                allow_duplicate=allow_duplicate,
                overrides=overrides,
            )
    except DuplicateSourceError as exc:
        console.print(f"[yellow]Duplicate detected:[/yellow] {exc}")
        raise SystemExit(2) from None
    except CaptureError as exc:
        console.print(f"[red]Capture failed:[/red] {exc}")
        raise SystemExit(1) from None
    _print_source_summary(source)


@capture.command(name="note")
@click.argument("text")
@_apply_options
def capture_note_cmd(
    text: str,
    why_interesting: str,
    title: str | None,
    access: str | None,
    copyright_risk: str | None,
    reliability: str | None,
    llm_allowed: bool | None,
    allow_duplicate: bool,
) -> None:
    """Erfasst eine eigene Notiz als Source."""
    p = get_paths()
    _ensure_registry_ready(p)
    overrides = _build_overrides(access, copyright_risk, reliability, llm_allowed)
    try:
        with registry_connect(p.registry_db) as conn:
            source = capture_note(
                text,
                why_interesting,
                conn=conn,
                paths=p,
                title=title,
                allow_duplicate=allow_duplicate,
                overrides=overrides,
            )
    except DuplicateSourceError as exc:
        console.print(f"[yellow]Duplicate detected:[/yellow] {exc}")
        raise SystemExit(2) from None
    except CaptureError as exc:
        console.print(f"[red]Capture failed:[/red] {exc}")
        raise SystemExit(1) from None
    _print_source_summary(source)


# --- Sources-Subgruppe ------------------------------------------------------


@cli.group()
def sources() -> None:
    """Quellen anzeigen, durchsuchen, prüfen."""


@sources.command(name="list")
@click.option("--limit", default=50, show_default=True)
@click.option("--status", default=None, help="Filter: captured|extracted|...")
def sources_list(limit: int, status: str | None) -> None:
    """Listet erfasste Quellen."""
    p = get_paths()
    if not p.registry_db.exists():
        console.print("[yellow]No registry yet.[/yellow] Run [bold]curiosity registry init[/bold].")
        return
    with registry_connect(p.registry_db) as conn:
        repo = SourceRepository(conn)
        if status:
            try:
                items = repo.list_by_status(SourceStatus(status), limit=limit)
            except ValueError:
                console.print(f"[red]Unknown status:[/red] {status}")
                raise SystemExit(1) from None
        else:
            items = repo.list_all(limit=limit)
    if not items:
        console.print("[dim]No sources captured yet.[/dim]")
        return
    table = Table(title=f"Sources ({len(items)})", show_lines=False)
    for column in ("id", "type", "title", "access", "status", "captured_at"):
        table.add_column(column, style="bold" if column == "id" else "")
    for s in items:
        table.add_row(
            s.id,
            s.source_type.value,
            (s.title or "")[:60],
            s.access.value,
            s.status.value,
            s.captured_at.isoformat(timespec="seconds"),
        )
    console.print(table)


@sources.command(name="show")
@click.argument("source_id")
def sources_show(source_id: str) -> None:
    """Zeigt eine einzelne Source mit allen Feldern."""
    p = get_paths()
    if not p.registry_db.exists():
        console.print("[red]No registry.[/red]")
        raise SystemExit(1)
    with registry_connect(p.registry_db) as conn:
        repo = SourceRepository(conn)
        source = repo.get(source_id)
    if source is None:
        console.print(f"[red]Source not found:[/red] {source_id}")
        raise SystemExit(1)
    _print_source_summary(source)


@sources.command(name="inbox")
def sources_inbox() -> None:
    """Listet noch unverarbeitete Quellen (Status=captured)."""
    p = get_paths()
    if not p.registry_db.exists():
        console.print("[yellow]No registry yet.[/yellow]")
        return
    with registry_connect(p.registry_db) as conn:
        items = SourceRepository(conn).list_by_status(SourceStatus.CAPTURED)
    if not items:
        console.print("[green]Inbox is clean — no pending sources.[/green]")
        return
    table = Table(title=f"Inbox ({len(items)} pending)", show_lines=False)
    for column in ("id", "type", "title", "why_interesting"):
        table.add_column(column, style="bold" if column == "id" else "")
    for s in items:
        table.add_row(
            s.id,
            s.source_type.value,
            (s.title or "")[:50],
            s.why_interesting[:60],
        )
    console.print(table)


# --- Extract / Ingest ------------------------------------------------------


@cli.command()
@click.argument("source_id")
def extract(source_id: str) -> None:
    """Extrahiert die Roh-Quelle nach ``extracted/<source_id>.md``."""
    p = get_paths()
    _ensure_registry_ready(p)
    try:
        with registry_connect(p.registry_db) as conn:
            result = extract_source(source_id, conn=conn, paths=p)
    except ExtractionError as exc:
        console.print(f"[red]Extraction failed:[/red] {exc}")
        raise SystemExit(1) from None
    if result.status == "extracted":
        console.print(
            f"[green]Extracted[/green] {result.source_id} via "
            f"{result.extractor} {result.extractor_version} "
            f"({result.output_chars} chars) -> {result.output_path}"
        )
        if result.warnings:
            console.print("[yellow]Warnings:[/yellow]")
            for warning in result.warnings:
                console.print(f"  - {warning}")
    else:
        console.print(
            f"[red]Extraction failed[/red] for {result.source_id}: {result.error_message}"
        )
        raise SystemExit(1)


@cli.command()
@click.argument("source_id")
@click.option(
    "--prompt-id",
    "prompt_id",
    default="ingest_v0_1",
    show_default=True,
    help="Prompt-ID aus prompts/agents/.",
)
def ingest(source_id: str, prompt_id: str) -> None:
    """Erzeugt aus einer extrahierten Source ein LLM-Proposal."""
    p = get_paths()
    _ensure_registry_ready(p)
    try:
        with registry_connect(p.registry_db) as conn:
            result = ingest_source(source_id, conn=conn, paths=p, prompt_id=prompt_id)
    except IngestError as exc:
        console.print(f"[red]Ingest failed:[/red] {exc}")
        raise SystemExit(1) from None

    if result.status == "pending":
        table = Table(title=f"Proposal: {result.proposal_id}", show_lines=False)
        table.add_column("Field", style="bold")
        table.add_column("Value")
        table.add_row("status", result.status)
        table.add_row("run_id", result.run_id or "")
        table.add_row("path", result.proposal_path or "")
        table.add_row("new_pages", str(result.new_pages_count))
        table.add_row("hard_facts", str(result.hard_facts_count))
        table.add_row("open_questions", str(result.open_questions_count))
        table.add_row("confidence", result.confidence or "")
        console.print(table)
    elif result.status == "quarantined":
        console.print(
            f"[yellow]Quarantined[/yellow] — case {result.quarantine_case_id}: "
            f"{result.error_message}"
        )
        if result.proposal_path:
            console.print(f"Marker: {result.proposal_path}")
        raise SystemExit(2)
    else:
        console.print(f"[red]Status: {result.status}[/red] — {result.error_message}")
        raise SystemExit(1)


# --- Proposal-Subgruppe ------------------------------------------------------


@cli.group()
def proposal() -> None:
    """Proposals anzeigen und reviewen (M3 erweitert dies)."""


@proposal.command(name="list")
@click.option("--status", default=None, help="Filter: pending|approved|rejected|quarantined")
@click.option("--limit", default=50, show_default=True)
def proposal_list(status: str | None, limit: int) -> None:
    """Listet Proposals."""
    p = get_paths()
    if not p.registry_db.exists():
        console.print("[yellow]No registry yet.[/yellow]")
        return
    with registry_connect(p.registry_db) as conn:
        repo = ProposalRepository(conn)
        items = repo.list_by_status(status, limit=limit) if status else repo.list_all(limit=limit)
    if not items:
        console.print("[dim]No proposals yet.[/dim]")
        return
    table = Table(title=f"Proposals ({len(items)})", show_lines=False)
    for column in ("id", "status", "risk", "pages", "facts", "confidence", "created_at"):
        table.add_column(column, style="bold" if column == "id" else "")
    for r in items:
        table.add_row(
            r.id,
            r.status,
            r.risk_level or "",
            str(r.new_pages_count),
            str(r.hard_facts_count),
            r.confidence or "",
            r.created_at.isoformat(timespec="seconds"),
        )
    console.print(table)


@proposal.command(name="show")
@click.argument("proposal_id")
def proposal_show(proposal_id: str) -> None:
    """Zeigt ein Proposal mit Pfad und Metadaten."""
    p = get_paths()
    if not p.registry_db.exists():
        console.print("[red]No registry.[/red]")
        raise SystemExit(1)
    with registry_connect(p.registry_db) as conn:
        record = ProposalRepository(conn).get(proposal_id)
    if record is None:
        console.print(f"[red]Proposal not found:[/red] {proposal_id}")
        raise SystemExit(1)
    table = Table(title=f"Proposal {record.id}", show_lines=False)
    table.add_column("Field", style="bold")
    table.add_column("Value")
    table.add_row("type", record.proposal_type)
    table.add_row("status", record.status)
    table.add_row("source_id", record.source_id or "")
    table.add_row("run_id", record.run_id or "")
    table.add_row("path", record.path)
    table.add_row("risk_level", record.risk_level or "")
    table.add_row("new_pages", str(record.new_pages_count))
    table.add_row("hard_facts", str(record.hard_facts_count))
    table.add_row("open_questions", str(record.open_questions_count))
    table.add_row("confidence", record.confidence or "")
    table.add_row("created_at", record.created_at.isoformat(timespec="seconds"))
    if record.reviewed_at:
        table.add_row("reviewed_at", record.reviewed_at.isoformat(timespec="seconds"))
        table.add_row("decision", record.review_decision or "")
    console.print(table)
    summary_path = p.root / record.path / "summary.md"
    if summary_path.exists():
        console.print(
            f"\n[dim]Read summary:[/dim] {summary_path}\n"
            "[dim]Approve/Reject Workflow folgt in M3.[/dim]"
        )


# --- Quarantine-Subgruppe ----------------------------------------------------


@cli.group()
def quarantine() -> None:
    """Offene Quarantäne-Fälle anzeigen."""


@quarantine.command(name="list")
def quarantine_list() -> None:
    """Listet offene Quarantäne-Fälle."""
    p = get_paths()
    if not p.registry_db.exists():
        console.print("[yellow]No registry yet.[/yellow]")
        return
    with registry_connect(p.registry_db) as conn:
        items = QuarantineRepository(conn).list_open()
    if not items:
        console.print("[green]No open quarantine cases.[/green]")
        return
    table = Table(title=f"Quarantine ({len(items)} open)", show_lines=False)
    for column in ("id", "type", "severity", "source_id", "created_at", "recommended"):
        table.add_column(column, style="bold" if column == "id" else "")
    for c in items:
        table.add_row(
            c.id,
            c.case_type,
            c.severity,
            c.source_id or "",
            c.created_at.isoformat(timespec="seconds"),
            (c.recommended_action or "")[:60],
        )
    console.print(table)


# --- Proposal approve / reject / request-changes ----------------------------


@proposal.command(name="approve")
@click.argument("proposal_id")
@click.option(
    "--auto-commit/--no-auto-commit",
    default=None,
    help="Override fuer CURIOSITY_PUBLISH_AUTO_COMMIT (default: env, sonst false).",
)
def proposal_approve(proposal_id: str, auto_commit: bool | None) -> None:
    """Veroeffentlicht ein Proposal nach wiki/ (Two-Phase Publish)."""
    p = get_paths()
    _ensure_registry_ready(p)
    try:
        with registry_connect(p.registry_db) as conn:
            result = publish_proposal(proposal_id, conn=conn, paths=p, auto_commit=auto_commit)
    except SlugCollisionError as exc:
        console.print(f"[yellow]Slug collision:[/yellow] {exc}")
        raise SystemExit(2) from None
    except PublishError as exc:
        console.print(f"[red]Publish failed:[/red] {exc}")
        raise SystemExit(1) from None

    console.print(
        f"[green]Approved[/green] {proposal_id}: "
        f"{len(result.pages_written)} page(s) written, "
        f"{result.claims_count} claim(s)."
    )
    for path in result.pages_written:
        console.print(f"  - {path}")
    if result.git_commit:
        console.print(f"[dim]Git commit: {result.git_commit[:12]}[/dim]")
    elif result.auto_commit_skipped_reason:
        console.print(f"[dim]Auto-commit skipped: {result.auto_commit_skipped_reason}[/dim]")


@proposal.command(name="reject")
@click.argument("proposal_id")
@click.option("--reason", default="rejected by user", help="Begruendung.")
def proposal_reject(proposal_id: str, reason: str) -> None:
    """Verwirft ein Proposal — kein Wiki-Schreib."""
    p = get_paths()
    _ensure_registry_ready(p)
    try:
        with registry_connect(p.registry_db) as conn:
            reject_proposal(proposal_id, conn=conn, reason=reason)
    except PublishError as exc:
        console.print(f"[red]Reject failed:[/red] {exc}")
        raise SystemExit(1) from None
    console.print(f"[yellow]Rejected[/yellow] {proposal_id}: {reason}")


@proposal.command(name="request-changes")
@click.argument("proposal_id")
@click.option("--notes", default="", help="Notizen fuer den naechsten Iteration.")
def proposal_request_changes(proposal_id: str, notes: str) -> None:
    """Setzt Status auf needs_changes und schreibt review_notes.md."""
    p = get_paths()
    _ensure_registry_ready(p)
    try:
        with registry_connect(p.registry_db) as conn:
            request_changes(proposal_id, conn=conn, paths=p, notes=notes)
    except PublishError as exc:
        console.print(f"[red]Request-changes failed:[/red] {exc}")
        raise SystemExit(1) from None
    console.print(f"[yellow]Changes requested[/yellow] for {proposal_id}")


# --- Pages-Subgruppe --------------------------------------------------------


@cli.group()
def pages() -> None:
    """Wiki-Pages anzeigen."""


@pages.command(name="list")
@click.option("--type", "page_type", default=None, help="Filter nach PageType.")
@click.option("--limit", default=50, show_default=True)
def pages_list(page_type: str | None, limit: int) -> None:
    """Listet veroeffentlichte Wiki-Pages."""
    from curiosity_wiki.wiki.models import PageType

    p = get_paths()
    if not p.registry_db.exists():
        console.print("[yellow]No registry yet.[/yellow]")
        return
    with registry_connect(p.registry_db) as conn:
        repo = PageRepository(conn)
        if page_type:
            try:
                items = repo.list_by_type(PageType(page_type), limit=limit)
            except ValueError:
                console.print(f"[red]Unknown page type:[/red] {page_type}")
                raise SystemExit(1) from None
        else:
            items = repo.list_all(limit=limit)
    if not items:
        console.print("[dim]No pages yet.[/dim]")
        return
    table = Table(title=f"Pages ({len(items)})", show_lines=False)
    for column in ("id", "type", "title", "freshness", "confidence", "updated_at"):
        table.add_column(column, style="bold" if column == "id" else "")
    for page in items:
        table.add_row(
            page.id,
            page.page_type.value,
            (page.title or "")[:50],
            page.freshness.value,
            page.confidence.value,
            page.updated_at.isoformat(timespec="seconds"),
        )
    console.print(table)


# --- Lint -------------------------------------------------------------------


@cli.command()
@click.option("--report/--no-report", default=True, help="Markdown-Report nach docs/_ops/.")
def lint(report: bool) -> None:
    """Wiki-Lint v0 (M3 Basisregeln)."""
    p = get_paths()
    _ensure_registry_ready(p)
    with registry_connect(p.registry_db) as conn:
        result = run_lint(conn, paths=p)

    if report:
        report_path = p.ops_logs / "lint_reports" / f"{result.run_id}.md"
        write_report_markdown(result, report_path)

    table = Table(title=f"Lint Run {result.run_id}", show_lines=False)
    table.add_column("Severity", style="bold")
    table.add_column("Count", justify="right")
    table.add_row("error", str(result.errors))
    table.add_row("warning", str(result.warnings))
    table.add_row("info", str(result.infos))
    console.print(table)
    for finding in result.findings[:25]:
        color = {
            LintSeverity.ERROR: "red",
            LintSeverity.WARNING: "yellow",
            LintSeverity.INFO: "dim",
        }[finding.severity]
        path_or_id = finding.file_path or finding.page_id or finding.source_id or "?"
        console.print(
            f"  [{color}]{finding.severity.value:>7s}[/{color}] "
            f"{finding.finding_type:<28s} {path_or_id}"
        )
        console.print(f"           [dim]{finding.message}[/dim]")
    if len(result.findings) > 25:
        console.print(f"[dim]... and {len(result.findings) - 25} more.[/dim]")
    if report:
        console.print(f"\n[dim]Report: docs/_ops/lint_reports/{result.run_id}.md[/dim]")
    if result.errors:
        raise SystemExit(1)


# --- Entry-Point ------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    """Entry-Point für ``python -m curiosity_wiki`` und ``curiosity``-Skript."""
    try:
        cli.main(args=argv, prog_name="curiosity", standalone_mode=True)
    except SystemExit as exc:
        return int(exc.code) if exc.code is not None else 0
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
