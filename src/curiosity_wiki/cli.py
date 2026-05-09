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
from curiosity_wiki.browse import (
    browse_by_collection,
    browse_by_topic,
    browse_random,
)
from curiosity_wiki.config import load_config
from curiosity_wiki.evals import run_golden_questions, write_golden_report
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
from curiosity_wiki.read_models import (
    read_model_status,
)
from curiosity_wiki.read_models import (
    rebuild_all as readmodels_rebuild_all,
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
from curiosity_wiki.search import (
    SearchError,
    rebuild_index_from_markdown,
    search_pages,
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
        "Aktuelle Phase: M5 Local Web UI. "
        "M1-M4 plus FastAPI-Backend, Jinja2-Templates, Read-Models und "
        "lokal startbare Web-UI (curiosity web run)."
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
        "\n[dim]Phase: M5 — Local Web UI. See docs/PROJECT_STATE.md for current state.[/dim]"
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
    """Wiki-Lint (13 Regeln; M3 Basis + M4 orphan_page, alias_collision)."""
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


# --- Search & Index (M4) -----------------------------------------------------


@cli.command()
@click.argument("query")
@click.option("--type", "page_type", default=None, help="Filter PageType (z.B. topic, recipe).")
@click.option(
    "--freshness", default=None, help="Filter Freshness (stable|periodic|volatile|personal)."
)
@click.option("--status", default=None, help="Filter Status (active|draft|archived).")
@click.option("--tag", default=None, help="Filter nach Tag-Substring.")
@click.option("--limit", default=20, show_default=True, type=int)
def search(
    query: str,
    page_type: str | None,
    freshness: str | None,
    status: str | None,
    tag: str | None,
    limit: int,
) -> None:
    """Volltextsuche ueber Wiki-Pages (FTS5, ADR-0014)."""
    p = get_paths()
    if not p.registry_db.exists():
        console.print("[yellow]No registry yet.[/yellow] Run [bold]curiosity registry init[/bold].")
        raise SystemExit(1)
    with registry_connect(p.registry_db) as conn:
        try:
            hits = search_pages(
                conn,
                query,
                page_type=page_type,
                freshness=freshness,
                status=status,
                tag=tag,
                limit=limit,
            )
        except SearchError as exc:
            console.print(f"[red]Search failed:[/red] {exc}")
            raise SystemExit(1) from None
    if not hits:
        console.print("[dim]No matches.[/dim]")
        return
    table = Table(title=f"Search: {query!r} ({len(hits)} hit(s))", show_lines=False)
    for column in ("rank", "type", "title", "freshness", "path"):
        table.add_column(column, style="bold" if column == "title" else "")
    for hit in hits:
        table.add_row(
            f"{hit.rank:.2f}",
            hit.page_type,
            hit.title[:50],
            hit.freshness,
            hit.relative_path,
        )
    console.print(table)
    for hit in hits[:5]:
        console.print(f"\n[bold]{hit.title}[/bold]  [dim]{hit.relative_path}[/dim]")
        console.print(f"  {hit.snippet}")


@cli.group()
def index() -> None:
    """Such-Index (FTS5) verwalten."""


@index.command(name="rebuild")
def index_rebuild() -> None:
    """Index komplett aus wiki/-Markdown neu erzeugen (ADR-0014)."""
    p = get_paths()
    _ensure_registry_ready(p)
    with registry_connect(p.registry_db) as conn:
        result = rebuild_index_from_markdown(conn, paths=p)
    table = Table(title="Index Rebuild", show_lines=False)
    table.add_column("Field", style="bold")
    table.add_column("Value")
    table.add_row("files_scanned", str(result.files_scanned))
    table.add_row("rows_written", str(result.rows_written))
    table.add_row("skipped", str(len(result.skipped)))
    console.print(table)
    if result.skipped:
        console.print("[yellow]Skipped:[/yellow]")
        for path, reason in result.skipped[:20]:
            console.print(f"  - {path}: {reason}")
        if len(result.skipped) > 20:
            console.print(f"  [dim]... and {len(result.skipped) - 20} more.[/dim]")


# --- Browse (M4) -----------------------------------------------------------


@cli.command()
@click.option("--random", "random_flag", is_flag=True, default=False, help="Zufaellige Pages.")
@click.option("--topic", default=None, help="Pages, die zu einer Topic-Page verlinken.")
@click.option("--collection", default=None, help="Pages aus einer Collection.")
@click.option("--limit", default=10, show_default=True, type=int)
def browse(random_flag: bool, topic: str | None, collection: str | None, limit: int) -> None:
    """Lesepfade durchs Wiki (M4)."""
    p = get_paths()
    if not p.registry_db.exists():
        console.print("[yellow]No registry yet.[/yellow] Run [bold]curiosity registry init[/bold].")
        raise SystemExit(1)
    flags = sum(1 for x in (random_flag, topic, collection) if x)
    if flags == 0:
        console.print("[red]Bitte einen Modus angeben:[/red] --random, --topic, oder --collection.")
        raise SystemExit(1)
    if flags > 1:
        console.print("[red]Nur ein Modus auf einmal:[/red] --random / --topic / --collection.")
        raise SystemExit(1)
    with registry_connect(p.registry_db) as conn:
        if random_flag:
            entries = browse_random(conn, limit=limit)
            title = f"Random ({len(entries)})"
        elif topic:
            entries = browse_by_topic(conn, topic, limit=limit)
            title = f"Topic '{topic}' ({len(entries)})"
        else:
            entries = browse_by_collection(conn, collection or "", limit=limit)
            title = f"Collection '{collection}' ({len(entries)})"
    if not entries:
        console.print("[dim]No entries.[/dim]")
        return
    table = Table(title=title, show_lines=False)
    for column in ("type", "title", "freshness", "path"):
        table.add_column(column, style="bold" if column == "title" else "")
    for entry in entries:
        table.add_row(
            entry.page_type,
            entry.title[:50],
            entry.freshness,
            entry.relative_path,
        )
    console.print(table)


# --- Open Questions / Freshness (M4) ---------------------------------------


@cli.group()
def questions() -> None:
    """Offene Fragen aus dem Wiki."""


@questions.command(name="list")
@click.option("--limit", default=50, show_default=True, type=int)
def questions_list(limit: int) -> None:
    """Aggregiert offene Fragen aus Question-Pages und Frontmatter."""
    from curiosity_wiki.wiki.aggregations import collect_open_questions

    p = get_paths()
    items = collect_open_questions(paths=p)
    if not items:
        console.print("[dim]No open questions.[/dim]")
        return
    table = Table(title=f"Open Questions ({len(items)})", show_lines=False)
    for column in ("source", "page", "question"):
        table.add_column(column, style="bold" if column == "question" else "")
    for item in items[:limit]:
        table.add_row(item.source, item.page_title[:30], item.text[:80])
    console.print(table)
    if len(items) > limit:
        console.print(f"[dim]... and {len(items) - limit} more.[/dim]")


@cli.command()
def freshness() -> None:
    """Freshness-Dashboard: ueberfaellige und volatile-ohne-schedule Pages."""
    from curiosity_wiki.wiki.aggregations import collect_freshness_status

    p = get_paths()
    if not p.registry_db.exists():
        console.print("[yellow]No registry yet.[/yellow]")
        raise SystemExit(1)
    with registry_connect(p.registry_db) as conn:
        report = collect_freshness_status(conn)

    table = Table(title="Freshness", show_lines=False)
    table.add_column("Bucket", style="bold")
    table.add_column("Count", justify="right")
    table.add_row("overdue", str(len(report.overdue)))
    table.add_row("due within 7 days", str(len(report.due_within_7_days)))
    table.add_row("volatile without schedule", str(len(report.volatile_without_schedule)))
    console.print(table)
    if report.overdue:
        console.print("\n[bold red]Overdue:[/bold red]")
        for entry in report.overdue[:20]:
            console.print(
                f"  - {entry.title} ({entry.page_type}) — "
                f"review_after {entry.review_after}, {entry.days_overdue}d overdue"
            )
    if report.volatile_without_schedule:
        console.print("\n[bold yellow]Volatile without schedule:[/bold yellow]")
        for entry in report.volatile_without_schedule[:20]:
            console.print(f"  - {entry.title} ({entry.page_type})")


# --- Eval Golden (M4) ------------------------------------------------------


@cli.group(name="eval")
def eval_group() -> None:
    """Evaluation-Runner (Golden Questions, ...)."""


@eval_group.command(name="golden")
@click.option(
    "--questions-file",
    "questions_file",
    default=None,
    type=click.Path(path_type=Path),
    help="Override fuer eval/golden-questions.yaml.",
)
@click.option("--report/--no-report", default=True, help="Markdown-Report nach docs/_ops/.")
def eval_golden(questions_file: Path | None, report: bool) -> None:
    """Fuehrt die Golden Questions aus und meldet Pass/Fail."""
    p = get_paths()
    _ensure_registry_ready(p)
    with registry_connect(p.registry_db) as conn:
        run = run_golden_questions(conn, paths=p, questions_file=questions_file)
    if report:
        from datetime import UTC, datetime

        stamp = datetime.now(tz=UTC).strftime("%Y%m%d-%H%M%S")
        report_path = p.ops_logs / "eval_reports" / f"golden-{stamp}.md"
        write_golden_report(run, report_path)

    table = Table(title=f"Golden Questions ({run.total})", show_lines=False)
    table.add_column("ID", style="bold")
    table.add_column("Type")
    table.add_column("Status")
    table.add_column("Detail")
    for result in run.results:
        color = "green" if result.passed else "red"
        status = "PASS" if result.passed else "FAIL"
        table.add_row(
            result.id,
            result.type,
            f"[{color}]{status}[/{color}]",
            result.detail[:60],
        )
    console.print(table)
    console.print(f"\nPassed: [green]{run.passed}[/green]  Failed: [red]{run.failed}[/red]")
    if report:
        console.print(f"[dim]Report: docs/_ops/eval_reports/golden-{stamp}.md[/dim]")
    if run.failed:
        raise SystemExit(1)


# --- Read Models (M5) -------------------------------------------------------


@cli.group(name="readmodels")
def readmodels_group() -> None:
    """Read-Models fuer die Web-UI verwalten (M5, ADR-0016)."""


@readmodels_group.command(name="rebuild")
def readmodels_rebuild_cmd() -> None:
    """Baut alle Read-Models neu aus Wiki-Markdown plus Registry."""
    p = get_paths()
    _ensure_registry_ready(p)
    with registry_connect(p.registry_db) as conn:
        result = readmodels_rebuild_all(conn, paths=p)
    table = Table(title="Read-Models Rebuild", show_lines=False)
    table.add_column("Field", style="bold")
    table.add_column("Value")
    table.add_row("pages_count", str(result.pages_count))
    table.add_row("written", str(len(result.written)))
    table.add_row("skipped", str(len(result.skipped)))
    console.print(table)
    for path in result.written:
        console.print(f"  + {path}")
    if result.skipped:
        console.print("[yellow]Skipped:[/yellow]")
        for name, reason in result.skipped:
            console.print(f"  - {name}: {reason}")


@readmodels_group.command(name="status")
def readmodels_status_cmd() -> None:
    """Zeigt Build-Status pro Read-Model."""
    p = get_paths()
    statuses = read_model_status(paths=p)
    table = Table(title="Read-Models Status", show_lines=False)
    for column in ("name", "exists", "schema", "built_at", "path"):
        table.add_column(column, style="bold" if column == "name" else "")
    for status in statuses:
        table.add_row(
            status.name,
            "yes" if status.exists else "no",
            str(status.schema_version) if status.schema_version is not None else "-",
            status.built_at or "-",
            status.path,
        )
    console.print(table)


# --- Web (M5) --------------------------------------------------------------


@cli.group()
def web() -> None:
    """Lokale Web-UI starten (FastAPI + Jinja2; M5, ADR-0015)."""


@web.command(name="run")
@click.option("--host", default="127.0.0.1", show_default=True, help="Bind-Host.")
@click.option("--port", default=8765, show_default=True, type=int, help="HTTP-Port.")
@click.option(
    "--reload/--no-reload",
    default=False,
    help="Auto-Reload bei Code-Aenderung (Dev).",
)
def web_run(host: str, port: int, reload: bool) -> None:
    """Startet den uvicorn-Server fuer die Curiosity-Web-UI."""
    import uvicorn

    p = get_paths()
    _ensure_registry_ready(p)
    console.print(f"[bold green]Starting Curiosity Web UI[/bold green] on http://{host}:{port}")
    if reload:
        console.print("[dim]reload mode — code changes restart the server[/dim]")
    uvicorn.run(
        "curiosity_wiki.web.app:create_app",
        host=host,
        port=port,
        factory=True,
        reload=reload,
    )


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
