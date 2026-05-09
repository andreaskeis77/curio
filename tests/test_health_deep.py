"""M6 Tests: /healthz/deep (ADR-0017)."""

from __future__ import annotations

import shutil
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from curiosity_wiki.paths import VaultPaths, get_paths
from curiosity_wiki.read_models import rebuild_all
from curiosity_wiki.registry import connect, migrate
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


def test_healthz_deep_degraded_without_read_models(
    client: TestClient, initialized_vault: VaultPaths
) -> None:
    """Frische Registry, keine Read-Models -> degraded mit 200."""
    response = client.get("/healthz/deep")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "degraded"
    assert payload["checks"]["registry"]["ok"] is True
    assert payload["checks"]["fts5"]["ok"] is True
    assert payload["checks"]["read_models"]["ok"] is False
    assert "site_index" in payload["checks"]["read_models"]["missing"]


def test_healthz_deep_ok_after_rebuild(client: TestClient, initialized_vault: VaultPaths) -> None:
    """Nach rebuild_all + wiki-Verzeichnis: Status ok."""
    initialized_vault.wiki.mkdir(parents=True, exist_ok=True)
    with connect(initialized_vault.registry_db) as conn:
        rebuild_all(conn, paths=initialized_vault)
    response = client.get("/healthz/deep")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["checks"]["read_models"]["ok"] is True
    assert payload["checks"]["wiki"]["ok"] is True


def test_healthz_deep_down_without_registry(tmp_path: Path) -> None:
    """Ohne Registry-DB liefert /healthz/deep Status down + 503."""
    (tmp_path / "pyproject.toml").write_text("[project]\nname='dummy'\n", encoding="utf-8")
    paths = VaultPaths(root=tmp_path)
    app = create_app(paths=paths)
    with TestClient(app) as test_client:
        response = test_client.get("/healthz/deep")
    assert response.status_code == 503
    payload = response.json()
    assert payload["status"] == "down"
    assert payload["checks"]["registry"]["ok"] is False


def test_healthz_plain_still_ok(client: TestClient) -> None:
    """Der einfache /healthz bleibt unabhaengig vom deep-Status verfuegbar."""
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.text == "ok"
