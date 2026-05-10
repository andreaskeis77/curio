"""M7 Tests: Scouts-API + Freshness-Dashboard-Erweiterung."""

from __future__ import annotations

import json
import shutil
from collections.abc import Iterator
from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient

from curiosity_wiki.config import CuriosityConfig
from curiosity_wiki.paths import VaultPaths, get_paths
from curiosity_wiki.read_models import READ_MODEL_FILES, rebuild_all
from curiosity_wiki.registry import connect, migrate
from curiosity_wiki.scouts import run_scout
from curiosity_wiki.web import create_app


@pytest.fixture
def vault(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> VaultPaths:
    (tmp_path / "pyproject.toml").write_text("[project]\nname='dummy'\n", encoding="utf-8")
    real = get_paths().prompts
    if real.exists():
        shutil.copytree(real, tmp_path / "prompts")
    monkeypatch.setenv("CURIOSITY_VAULT_ROOT", str(tmp_path))
    return VaultPaths(root=tmp_path)


@pytest.fixture
def initialized_vault(vault: VaultPaths) -> VaultPaths:
    with connect(vault.registry_db) as connection:
        migrate(connection)
    return vault


@pytest.fixture
def client(initialized_vault: VaultPaths) -> Iterator[TestClient]:
    app = create_app(paths=initialized_vault)
    with TestClient(app) as test_client:
        yield test_client


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


def _minimal_scout(scout_id: str = "tiny") -> dict:
    return {
        "id": scout_id,
        "domain": "places",
        "prompt_id": "ingest_v0_1",
        "frequency_hours": 0,
        "sources": [{"type": "note", "value": "First api note.", "title": "First"}],
    }


def test_api_list_scouts_empty(client: TestClient) -> None:
    response = client.get("/api/scouts")
    assert response.status_code == 200
    assert response.json() == {"count": 0, "items": []}


def test_api_list_scouts_returns_definition(
    client: TestClient, initialized_vault: VaultPaths
) -> None:
    _write_scout(initialized_vault, "tiny", _minimal_scout())
    response = client.get("/api/scouts")
    payload = response.json()
    assert payload["count"] == 1
    assert payload["items"][0]["id"] == "tiny"
    assert payload["items"][0]["last_run"] is None


def test_api_scout_detail_shows_recent_runs(
    client: TestClient,
    initialized_vault: VaultPaths,
    mock_config: CuriosityConfig,
) -> None:
    _write_scout(initialized_vault, "tiny", _minimal_scout())
    with connect(initialized_vault.registry_db) as conn:
        run_scout("tiny", conn=conn, paths=initialized_vault, config=mock_config, force=True)
    response = client.get("/api/scouts/tiny")
    payload = response.json()
    assert payload["id"] == "tiny"
    assert payload["sources"][0]["type"] == "note"
    assert len(payload["recent_runs"]) >= 1
    assert payload["recent_runs"][0]["status"] == "completed"


def test_api_scout_detail_404(client: TestClient) -> None:
    assert client.get("/api/scouts/missing").status_code == 404


def test_freshness_dashboard_includes_scouts_section(
    client: TestClient,
    initialized_vault: VaultPaths,
    mock_config: CuriosityConfig,
) -> None:
    """rebuild_all schreibt freshness_dashboard.json mit scouts-Section."""
    _write_scout(initialized_vault, "tiny", _minimal_scout())
    with connect(initialized_vault.registry_db) as conn:
        run_scout("tiny", conn=conn, paths=initialized_vault, config=mock_config, force=True)
        rebuild_all(conn, paths=initialized_vault)
    payload = json.loads(
        (initialized_vault.read_models / READ_MODEL_FILES["freshness_dashboard"]).read_text(
            encoding="utf-8"
        )
    )
    scouts = payload["data"]["scouts"]
    assert len(scouts) == 1
    assert scouts[0]["scout_id"] == "tiny"
    assert scouts[0]["last_status"] == "completed"
