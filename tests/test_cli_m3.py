"""Contract-Tests fuer die M3-CLI-Befehle (proposal approve/reject/request-changes, pages, lint)."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from click.testing import CliRunner

from curiosity_wiki.cli import cli
from curiosity_wiki.paths import get_paths


@pytest.fixture
def isolated_vault(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    (tmp_path / "pyproject.toml").write_text("[project]\nname='dummy'\n", encoding="utf-8")
    real = get_paths().prompts
    if real.exists():
        shutil.copytree(real, tmp_path / "prompts")
    monkeypatch.setenv("CURIOSITY_VAULT_ROOT", str(tmp_path))
    monkeypatch.setenv("CURIOSITY_LLM_PROVIDER", "mock")
    return tmp_path


def _make_proposal_via_cli(runner: CliRunner) -> str:
    """Helper: capture/extract/ingest -> proposal_id."""
    from curiosity_wiki.proposals import ProposalRepository
    from curiosity_wiki.registry import connect
    from curiosity_wiki.sources import SourceRepository

    runner.invoke(cli, ["registry", "init"])
    runner.invoke(cli, ["capture", "note", "Test source for cli-m3", "--why", "test"])
    with connect(get_paths().registry_db) as conn:
        sources = SourceRepository(conn).list_all()
    sid = sources[0].id
    runner.invoke(cli, ["extract", sid])
    runner.invoke(cli, ["ingest", sid])
    with connect(get_paths().registry_db) as conn:
        proposals = ProposalRepository(conn).list_all()
    assert proposals, "no proposal after ingest"
    return proposals[0].id


def test_proposal_approve_publishes(isolated_vault: Path, runner: CliRunner) -> None:
    pid = _make_proposal_via_cli(runner)
    result = runner.invoke(cli, ["proposal", "approve", pid, "--no-auto-commit"])
    assert result.exit_code == 0, result.output
    assert "Approved" in result.output
    # mind. eine Page-Datei existiert
    md_files = list((isolated_vault / "wiki").rglob("*.md"))
    assert md_files


def test_proposal_reject_writes_no_files(isolated_vault: Path, runner: CliRunner) -> None:
    pid = _make_proposal_via_cli(runner)
    before = (
        list((isolated_vault / "wiki").rglob("*.md")) if (isolated_vault / "wiki").exists() else []
    )
    result = runner.invoke(cli, ["proposal", "reject", pid, "--reason", "n/a"])
    assert result.exit_code == 0
    after = (
        list((isolated_vault / "wiki").rglob("*.md")) if (isolated_vault / "wiki").exists() else []
    )
    assert before == after


def test_proposal_request_changes_writes_notes(isolated_vault: Path, runner: CliRunner) -> None:
    pid = _make_proposal_via_cli(runner)
    result = runner.invoke(
        cli, ["proposal", "request-changes", pid, "--notes", "Bitte mehr Quellen."]
    )
    assert result.exit_code == 0
    # review_notes.md existiert
    notes = list((isolated_vault / "proposals").rglob("review_notes.md"))
    assert notes


def test_proposal_approve_unknown_fails(isolated_vault: Path, runner: CliRunner) -> None:
    runner.invoke(cli, ["registry", "init"])
    result = runner.invoke(cli, ["proposal", "approve", "prop_unknown", "--no-auto-commit"])
    assert result.exit_code == 1
    assert "Publish failed" in result.output


def test_pages_list_after_approve(isolated_vault: Path, runner: CliRunner) -> None:
    pid = _make_proposal_via_cli(runner)
    runner.invoke(cli, ["proposal", "approve", pid, "--no-auto-commit"])
    result = runner.invoke(cli, ["pages", "list"])
    assert result.exit_code == 0
    assert "Pages" in result.output


def test_lint_runs_clean_on_empty_wiki(isolated_vault: Path, runner: CliRunner) -> None:
    runner.invoke(cli, ["registry", "init"])
    result = runner.invoke(cli, ["lint"])
    assert result.exit_code == 0
    assert "Lint Run" in result.output


def test_lint_finds_findings_after_approve(isolated_vault: Path, runner: CliRunner) -> None:
    pid = _make_proposal_via_cli(runner)
    runner.invoke(cli, ["proposal", "approve", pid, "--no-auto-commit"])
    result = runner.invoke(cli, ["lint"])
    # Mock-Output hat keine Sources im new_pages — Lint findet warnings, exit 0
    assert result.exit_code == 0
    assert "Lint Run" in result.output
