"""Curiosity Wiki CLI.

T0.1-Skelett: ``--help``, ``--version``, ``paths``, ``info``.
Reale Capture/Extract/Ingest-Befehle entstehen ab M1.
"""

from __future__ import annotations

import sys

import click
from rich.console import Console
from rich.table import Table

from curiosity_wiki import __version__
from curiosity_wiki.config import load_config
from curiosity_wiki.paths import get_paths

console = Console()


@click.group(
    help=(
        "Curiosity Wiki — persönliches, quellengestütztes Wissenssystem.\n\n"
        "Stand T0.1 (Method & Architecture Baseline). "
        "Reale Befehle (capture, extract, ingest, lint, search) folgen ab M1."
    )
)
@click.version_option(version=__version__, prog_name="curiosity")
def cli() -> None:
    """Top-Level-Group."""


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
    """Zeigt Version, Config und Status (T0.1)."""
    cfg = load_config()
    table = Table(title=f"Curiosity Wiki v{__version__}", show_lines=False)
    table.add_column("Setting", style="bold")
    table.add_column("Value")
    table.add_row("version", __version__)
    table.add_row("llm_provider", cfg.llm_provider)
    table.add_row("llm_model", cfg.llm_model or "(default)")
    table.add_row("log_level", cfg.log_level)
    table.add_row("dev_fail_fast", str(cfg.dev_fail_fast))
    table.add_row("agent_dry_run", str(cfg.agent_dry_run))
    console.print(table)
    console.print(
        "\n[dim]Phase: T0.1 — Method & Architecture Baseline. "
        "See docs/PROJECT_STATE.md for current state.[/dim]"
    )


@cli.command(name="quality-gates")
def quality_gates() -> None:
    """Platzhalter für ``tools/run_quality_gates.py``.

    In T0.1 verweist diese Subcommand nur auf den Aufruf — die Logik
    bleibt im Tools-Skript, damit sie auch ohne Paket-Install läuft.
    """
    console.print(
        "Quality Gates run via: [bold]python tools/run_quality_gates.py[/bold]\n"
        "(Subcommand bleibt T0.1 ein dünner Wrapper.)"
    )


def main(argv: list[str] | None = None) -> int:
    """Entry-Point für ``python -m curiosity_wiki`` und ``curiosity``-Skript.

    Click kümmert sich um System-Exit; wir geben hier 0 zurück, falls
    Click die Funktion direkt aufruft (Tests).
    """
    try:
        cli.main(args=argv, prog_name="curiosity", standalone_mode=True)
    except SystemExit as exc:
        return int(exc.code) if exc.code is not None else 0
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
