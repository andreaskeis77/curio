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
from curiosity_wiki.paths import VaultPaths, get_paths
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

console = Console()


@click.group(
    help=(
        "Curiosity Wiki — persönliches, quellengestütztes Wissenssystem.\n\n"
        "Aktuelle Phase: M1 Registry Spine. "
        "Capture (url/file/note), Registry (init/check), Sources (list/show/inbox)."
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
        "\n[dim]Phase: M1 — Registry Spine. See docs/PROJECT_STATE.md for current state.[/dim]"
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
