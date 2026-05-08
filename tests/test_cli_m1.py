"""Contract-Tests für die M1-CLI-Befehle.

Wir setzen ``CURIOSITY_VAULT_ROOT`` auf ein tmp-Verzeichnis und führen
die Click-Commands über CliRunner aus. Kein realer HTTP-Zugriff.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from curiosity_wiki.cli import cli


@pytest.fixture
def isolated_vault(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    (tmp_path / "pyproject.toml").write_text("[project]\nname='dummy'\n", encoding="utf-8")
    monkeypatch.setenv("CURIOSITY_VAULT_ROOT", str(tmp_path))
    return tmp_path


def test_registry_init_creates_db(isolated_vault: Path, runner: CliRunner) -> None:
    result = runner.invoke(cli, ["registry", "init"])
    assert result.exit_code == 0, result.output
    db = isolated_vault / "data" / "registry" / "curiosity.sqlite"
    assert db.exists()
    assert "Schema version: 1" in result.output


def test_registry_check_fails_without_init(isolated_vault: Path, runner: CliRunner) -> None:
    result = runner.invoke(cli, ["registry", "check"])
    assert result.exit_code != 0
    assert "does not exist" in result.output


def test_registry_check_passes_after_init(isolated_vault: Path, runner: CliRunner) -> None:
    runner.invoke(cli, ["registry", "init"])
    result = runner.invoke(cli, ["registry", "check"])
    assert result.exit_code == 0, result.output
    assert "Registry OK" in result.output


def test_capture_note_via_cli(isolated_vault: Path, runner: CliRunner) -> None:
    runner.invoke(cli, ["registry", "init"])
    result = runner.invoke(
        cli,
        ["capture", "note", "Mein Test", "--why", "Test"],
    )
    assert result.exit_code == 0, result.output
    assert "Captured: src_" in result.output


def test_sources_list_after_capture(isolated_vault: Path, runner: CliRunner) -> None:
    """Smoke: list-Command läuft erfolgreich, Registry hat 2 Sources."""
    from curiosity_wiki.registry import connect
    from curiosity_wiki.sources import SourceRepository

    runner.invoke(cli, ["registry", "init"])
    runner.invoke(cli, ["capture", "note", "Erster Eintrag", "--why", "x"])
    runner.invoke(cli, ["capture", "note", "Zweiter Eintrag", "--why", "y"])
    result = runner.invoke(cli, ["sources", "list"])
    assert result.exit_code == 0
    db = isolated_vault / "data" / "registry" / "curiosity.sqlite"
    with connect(db) as conn:
        assert SourceRepository(conn).count() == 2


def test_sources_inbox_shows_pending(isolated_vault: Path, runner: CliRunner) -> None:
    runner.invoke(cli, ["registry", "init"])
    runner.invoke(cli, ["capture", "note", "Inbox-Test", "--why", "x"])
    result = runner.invoke(cli, ["sources", "inbox"])
    assert result.exit_code == 0
    assert "Inbox" in result.output


def test_sources_show_known(isolated_vault: Path, runner: CliRunner) -> None:
    """show-Command zeigt eine zuvor gespeicherte Source mit voller ID."""
    from curiosity_wiki.registry import connect
    from curiosity_wiki.sources import SourceRepository

    runner.invoke(cli, ["registry", "init"])
    runner.invoke(cli, ["capture", "note", "Show-Test", "--why", "x"])
    db = isolated_vault / "data" / "registry" / "curiosity.sqlite"
    with connect(db) as conn:
        sources = SourceRepository(conn).list_all()
    assert len(sources) == 1
    source_id = sources[0].id
    result = runner.invoke(cli, ["sources", "show", source_id])
    assert result.exit_code == 0
    # ID kann von Rich getruncated werden — Prefix muss aber drin sein
    assert source_id[:20] in result.output


def test_sources_show_unknown_fails(isolated_vault: Path, runner: CliRunner) -> None:
    runner.invoke(cli, ["registry", "init"])
    result = runner.invoke(cli, ["sources", "show", "src_99999999_999999_ZZZZ"])
    assert result.exit_code != 0
    assert "not found" in result.output


def test_capture_duplicate_returns_exit_code_2(isolated_vault: Path, runner: CliRunner) -> None:
    runner.invoke(cli, ["registry", "init"])
    runner.invoke(cli, ["capture", "note", "Dupe", "--why", "x"])
    result = runner.invoke(cli, ["capture", "note", "Dupe", "--why", "y"])
    assert result.exit_code == 2
    assert "Duplicate" in result.output


def test_capture_with_allow_duplicate_succeeds(isolated_vault: Path, runner: CliRunner) -> None:
    runner.invoke(cli, ["registry", "init"])
    runner.invoke(cli, ["capture", "note", "DupeForce", "--why", "x"])
    result = runner.invoke(
        cli,
        ["capture", "note", "DupeForce", "--why", "y", "--allow-duplicate"],
    )
    assert result.exit_code == 0


def test_capture_file_via_cli(isolated_vault: Path, runner: CliRunner, tmp_path: Path) -> None:
    runner.invoke(cli, ["registry", "init"])
    payload = tmp_path / "doc.txt"
    payload.write_text("test content", encoding="utf-8")
    result = runner.invoke(
        cli,
        ["capture", "file", str(payload), "--why", "Reference doc"],
    )
    assert result.exit_code == 0, result.output
    assert "Captured: src_" in result.output


def test_info_shows_phase(isolated_vault: Path, runner: CliRunner) -> None:
    result = runner.invoke(cli, ["info"])
    assert result.exit_code == 0
    assert "M1" in result.output
