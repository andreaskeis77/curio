"""CLI Contract Tests."""

from __future__ import annotations

from click.testing import CliRunner

from curiosity_wiki import __version__
from curiosity_wiki.cli import cli


def test_cli_help_succeeds(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "Curiosity Wiki" in result.output


def test_cli_version(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.output


def test_cli_paths_command(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["paths"])
    assert result.exit_code == 0
    assert "root" in result.output
    assert "wiki" in result.output


def test_cli_info_command(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["info"])
    assert result.exit_code == 0
    assert "Curiosity Wiki" in result.output


def test_cli_quality_gates_command(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["quality-gates"])
    assert result.exit_code == 0
    assert "run_quality_gates" in result.output


def test_cli_unknown_command_fails(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["does-not-exist"])
    assert result.exit_code != 0
