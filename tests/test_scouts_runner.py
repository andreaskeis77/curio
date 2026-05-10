"""M7 Tests: Scout-Runner (ADR-0019)."""

from __future__ import annotations

import json
import os
import shutil
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
import yaml

from curiosity_wiki.config import CuriosityConfig
from curiosity_wiki.paths import VaultPaths, get_paths
from curiosity_wiki.registry import connect, migrate
from curiosity_wiki.scouts import (
    LockBusyError,
    ScoutRunResult,
    run_scout,
)
from curiosity_wiki.scouts.locks import (
    STALE_THRESHOLD,
    acquire_lock,
    release_lock,
)


@pytest.fixture
def vault(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> VaultPaths:
    (tmp_path / "pyproject.toml").write_text("[project]\nname='dummy'\n", encoding="utf-8")
    real = get_paths().prompts
    if real.exists():
        shutil.copytree(real, tmp_path / "prompts")
    monkeypatch.setenv("CURIOSITY_VAULT_ROOT", str(tmp_path))
    return VaultPaths(root=tmp_path)


@pytest.fixture
def conn(vault: VaultPaths) -> Iterator:
    with connect(vault.registry_db) as connection:
        migrate(connection)
        yield connection


@pytest.fixture
def mock_config() -> CuriosityConfig:
    return CuriosityConfig(
        llm_provider="mock",
        llm_model="",
        llm_temperature=0,
        llm_timeout_seconds=30,
        log_level="INFO",
        log_format="text",
        web_host="127.0.0.1",
        web_port=8765,
        dev_fail_fast=True,
        agent_dry_run=True,
    )


def _write_scout(vault: VaultPaths, scout_id: str, payload: dict) -> Path:
    base = vault.root / "scouts"
    base.mkdir(parents=True, exist_ok=True)
    target = base / f"{scout_id}.yaml"
    target.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return target


def _minimal_scout(scout_id: str = "tiny", **overrides) -> dict:
    base = {
        "id": scout_id,
        "domain": "places",
        "prompt_id": "ingest_v0_1",
        "frequency_hours": 0,  # erlauben sofortigen Re-Run im Test
        "sources": [
            {"type": "note", "value": "First note for tiny scout.", "title": "First"},
            {"type": "note", "value": "Second note for tiny scout.", "title": "Second"},
        ],
    }
    base.update(overrides)
    return base


def test_run_scout_creates_proposals_and_run_log(
    vault: VaultPaths, conn, mock_config: CuriosityConfig
) -> None:
    _write_scout(vault, "tiny", _minimal_scout())
    result = run_scout("tiny", conn=conn, paths=vault, config=mock_config)
    assert isinstance(result, ScoutRunResult)
    assert result.status == "completed"
    assert result.sources_seen == 2
    assert result.captured == 2
    assert result.proposals == 2
    assert result.quarantined == 0
    assert len(result.proposal_ids) == 2

    # scout_runs-Eintrag
    row = conn.execute("SELECT * FROM scout_runs WHERE id = ?", (result.run_id,)).fetchone()
    assert row is not None
    assert row["status"] == "completed"
    assert row["proposals"] == 2

    # Run-Log existiert
    log_path = vault.root / result.log_path
    assert log_path.exists()
    text = log_path.read_text(encoding="utf-8")
    assert "Scout Run" in text
    assert "completed" in text


def test_run_scout_dry_run_makes_no_proposals(
    vault: VaultPaths, conn, mock_config: CuriosityConfig
) -> None:
    _write_scout(vault, "tiny", _minimal_scout())
    result = run_scout("tiny", conn=conn, paths=vault, config=mock_config, dry_run=True)
    assert result.status == "completed"
    assert result.sources_seen == 2
    assert result.captured == 0
    assert result.proposals == 0
    assert result.skipped == 2


def test_run_scout_skipped_when_within_frequency(
    vault: VaultPaths, conn, mock_config: CuriosityConfig
) -> None:
    """Zweiter Lauf innerhalb frequency_hours wird mit status=skipped abgebrochen."""
    _write_scout(vault, "tiny", _minimal_scout(frequency_hours=24))
    first = run_scout("tiny", conn=conn, paths=vault, config=mock_config, force=True)
    assert first.status == "completed"

    second = run_scout("tiny", conn=conn, paths=vault, config=mock_config)
    assert second.status == "skipped"
    assert second.proposals == 0


def test_run_scout_force_runs_again_within_frequency(
    vault: VaultPaths, conn, mock_config: CuriosityConfig
) -> None:
    _write_scout(vault, "tiny", _minimal_scout(frequency_hours=24))
    run_scout("tiny", conn=conn, paths=vault, config=mock_config, force=True)
    second = run_scout(
        "tiny",
        conn=conn,
        paths=vault,
        config=mock_config,
        dry_run=True,  # dry-run vermeidet Duplicate-Capture im zweiten Lauf
        force=True,
    )
    assert second.status == "completed"
    assert second.sources_seen == 2


def test_run_scout_max_sources_limit(vault: VaultPaths, conn, mock_config: CuriosityConfig) -> None:
    payload = _minimal_scout()
    payload["sources"] = [
        {"type": "note", "value": f"note {i}", "title": f"n{i}"} for i in range(5)
    ]
    payload["limits"] = {"max_sources_per_run": 2}
    _write_scout(vault, "tiny", payload)
    result = run_scout("tiny", conn=conn, paths=vault, config=mock_config)
    assert result.sources_seen == 2  # gekappt durch max_sources_per_run


def test_run_scout_lock_blocks_parallel(vault: VaultPaths, conn) -> None:
    """Wenn ein anderer Prozess das Lock-File haelt, faellt der Run als skipped zurueck."""
    _write_scout(vault, "tiny", _minimal_scout())
    lock_path = vault.root / "data" / "scout_locks" / "tiny.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "pid": os.getpid(),
        "started_at": datetime.now(tz=UTC).isoformat(timespec="seconds"),
        "host": "test-host",
    }
    lock_path.write_text(json.dumps(payload), encoding="utf-8")

    result = run_scout("tiny", conn=conn, paths=vault, force=True)
    assert result.status == "skipped"
    assert "lock" in (result.error_message or "").lower()

    lock_path.unlink()


def test_lock_stale_after_threshold(tmp_path: Path) -> None:
    """Stale-Locks (alt > STALE_THRESHOLD) werden uebernommen."""
    lock = tmp_path / "stale.lock"
    lock.parent.mkdir(parents=True, exist_ok=True)
    lock.write_text(
        json.dumps(
            {
                "pid": 999999,
                "started_at": (
                    datetime.now(tz=UTC) - STALE_THRESHOLD - timedelta(hours=1)
                ).isoformat(),
                "host": "old",
            }
        ),
        encoding="utf-8",
    )
    # Sollte ohne Exception akquiriert werden (stale)
    acquire_lock(lock)
    assert lock.exists()
    payload = json.loads(lock.read_text(encoding="utf-8"))
    assert payload["pid"] == os.getpid()
    release_lock(lock)


def test_lock_busy_raises_when_fresh(tmp_path: Path) -> None:
    lock = tmp_path / "busy.lock"
    lock.write_text(
        json.dumps(
            {
                "pid": os.getpid(),
                "started_at": datetime.now(tz=UTC).isoformat(),
                "host": "x",
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(LockBusyError):
        acquire_lock(lock)
    lock.unlink()


def test_run_scout_idempotent_capture_marks_unchanged(
    vault: VaultPaths, conn, mock_config: CuriosityConfig
) -> None:
    """Zweiter Lauf mit force=True: Capture meldet Duplicate -> action=unchanged."""
    _write_scout(vault, "tiny", _minimal_scout(frequency_hours=0))
    first = run_scout("tiny", conn=conn, paths=vault, config=mock_config, force=True)
    assert first.captured == 2

    second = run_scout("tiny", conn=conn, paths=vault, config=mock_config, force=True)
    # gleiche Notes -> DuplicateSourceError -> outcome action=unchanged
    assert second.skipped == 2
    assert second.captured == 0
    assert second.errors == 0


def test_run_scout_writes_scout_runs_for_skipped(
    vault: VaultPaths, conn, mock_config: CuriosityConfig
) -> None:
    """Auch skipped runs landen in scout_runs."""
    _write_scout(vault, "tiny", _minimal_scout(frequency_hours=24))
    run_scout("tiny", conn=conn, paths=vault, config=mock_config, force=True)
    skipped = run_scout("tiny", conn=conn, paths=vault, config=mock_config)
    assert skipped.status == "skipped"
    rows = conn.execute("SELECT status FROM scout_runs ORDER BY started_at").fetchall()
    statuses = [row["status"] for row in rows]
    assert "completed" in statuses
    assert "skipped" in statuses
