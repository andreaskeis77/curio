"""M5 Tests: FastAPI JSON-API."""

from __future__ import annotations

import shutil
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient

from curiosity_wiki.config import CuriosityConfig
from curiosity_wiki.extraction import extract_source
from curiosity_wiki.linting import run_lint
from curiosity_wiki.paths import VaultPaths, get_paths
from curiosity_wiki.proposals import ingest_source
from curiosity_wiki.read_models import rebuild_all
from curiosity_wiki.registry import connect, migrate
from curiosity_wiki.sources import capture_note
from curiosity_wiki.web import create_app
from curiosity_wiki.wiki import publish_proposal
from curiosity_wiki.wiki.frontmatter import render_frontmatter
from curiosity_wiki.wiki.models import (
    ConfidenceLevel,
    Freshness,
    Page,
    PageStatus,
    PageType,
)
from curiosity_wiki.wiki.repository import LinkRepository, PageRepository


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
    """Registry initialized so that endpoints don't return 503."""
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


def _make_page(repo: PageRepository, *, page_id: str, title: str, slug: str) -> Page:
    now = datetime.now(tz=UTC)
    page = Page(
        id=page_id,
        title=title,
        slug=slug,
        page_type=PageType.TOPIC,
        status=PageStatus.ACTIVE,
        freshness=Freshness.STABLE,
        confidence=ConfidenceLevel.MEDIUM,
        created_at=now,
        updated_at=now,
        sources=[],
        why_interesting="api test",
        llm_generated=False,
        human_reviewed=True,
        reviewed_at=now,
    )
    repo.insert(page)
    return page


def _write_md(vault: VaultPaths, page: Page, body: str = "Test body content.") -> None:
    front = render_frontmatter(page)
    target = vault.root / page.relative_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(front + "\n# " + page.title + "\n\n" + body, encoding="utf-8")


def test_health_returns_ok(client: TestClient) -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert "version" in payload
    assert "read_models" in payload


def test_healthz_plain_text(client: TestClient) -> None:
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.text == "ok"


def test_pages_list_empty(client: TestClient) -> None:
    response = client.get("/api/pages")
    assert response.status_code == 200
    assert response.json() == {"count": 0, "items": []}


def test_pages_list_after_insert(client: TestClient, initialized_vault: VaultPaths) -> None:
    with connect(initialized_vault.registry_db) as conn:
        _make_page(PageRepository(conn), page_id="page_TAPIA", title="API Page", slug="api-page")
    response = client.get("/api/pages")
    payload = response.json()
    assert payload["count"] == 1
    assert payload["items"][0]["title"] == "API Page"


def test_pages_list_invalid_type_returns_400(client: TestClient) -> None:
    response = client.get("/api/pages?type=not-a-type")
    assert response.status_code == 400


def test_pages_detail_404_when_missing(client: TestClient) -> None:
    response = client.get("/api/pages/page_DOES_NOT_EXIST")
    assert response.status_code == 404


def test_pages_detail_returns_body_and_backlinks(
    client: TestClient, initialized_vault: VaultPaths
) -> None:
    with connect(initialized_vault.registry_db) as conn:
        repo = PageRepository(conn)
        target = _make_page(repo, page_id="page_TARG", title="Target", slug="target")
        caller = _make_page(repo, page_id="page_CALL", title="Caller", slug="caller")
        _write_md(initialized_vault, target, body="Target body.")
        _write_md(initialized_vault, caller, body="Sees [[Target]].")
        LinkRepository(conn).insert(
            from_page_id=caller.id,
            to_page_id=target.id,
            target_text="Target",
            status="resolved",
        )
    response = client.get(f"/api/pages/{target.id}")
    payload = response.json()
    assert response.status_code == 200
    assert "Target body." in payload["body_markdown"]
    assert payload["backlinks"][0]["id"] == caller.id


def test_search_endpoint_finds_published_page(
    client: TestClient,
    initialized_vault: VaultPaths,
    mock_config: CuriosityConfig,
) -> None:
    """Mock-Provider produziert 'Mock Topic' — Search findet's per Body."""
    with connect(initialized_vault.registry_db) as conn:
        source = capture_note("API-Source", why_interesting="x", conn=conn, paths=initialized_vault)
        extract_source(source.id, conn=conn, paths=initialized_vault)
        result = ingest_source(source.id, conn=conn, paths=initialized_vault, config=mock_config)
        publish_proposal(result.proposal_id, conn=conn, paths=initialized_vault, auto_commit=False)
    response = client.get("/api/search?q=Mock")
    assert response.status_code == 200
    titles = [item["title"] for item in response.json()["items"]]
    assert "Mock Topic" in titles


def test_search_invalid_filter_returns_400(client: TestClient) -> None:
    response = client.get("/api/search?q=x&type=not-a-type")
    assert response.status_code == 400


def test_browse_random_walk_endpoint(client: TestClient, initialized_vault: VaultPaths) -> None:
    with connect(initialized_vault.registry_db) as conn:
        _make_page(PageRepository(conn), page_id="page_BR", title="BR", slug="br")
    response = client.get("/api/browse/random-walk?n=3")
    payload = response.json()
    assert response.status_code == 200
    assert payload["count"] >= 1


def test_browse_topic_unknown_returns_empty(client: TestClient) -> None:
    response = client.get("/api/browse/topic/Definitely-Unknown-XYZ")
    assert response.status_code == 200
    assert response.json()["count"] == 0


def test_proposals_list(
    client: TestClient,
    initialized_vault: VaultPaths,
    mock_config: CuriosityConfig,
) -> None:
    with connect(initialized_vault.registry_db) as conn:
        source = capture_note("P-Source", why_interesting="x", conn=conn, paths=initialized_vault)
        extract_source(source.id, conn=conn, paths=initialized_vault)
        ingest_source(source.id, conn=conn, paths=initialized_vault, config=mock_config)
    response = client.get("/api/proposals")
    payload = response.json()
    assert response.status_code == 200
    assert payload["count"] >= 1


def test_lint_report_404_without_run(client: TestClient) -> None:
    response = client.get("/api/lint/report/latest")
    assert response.status_code == 404


def test_lint_report_after_run(client: TestClient, initialized_vault: VaultPaths) -> None:
    with connect(initialized_vault.registry_db) as conn:
        run_lint(conn, paths=initialized_vault)
    response = client.get("/api/lint/report/latest")
    assert response.status_code == 200
    body = response.json()
    assert "run_id" in body
    assert "findings" in body


def test_health_reflects_built_read_models(
    client: TestClient, initialized_vault: VaultPaths
) -> None:
    """Nach rebuild_all melden read_models exists=True."""
    with connect(initialized_vault.registry_db) as conn:
        rebuild_all(conn, paths=initialized_vault)
    response = client.get("/api/health")
    payload = response.json()
    rm_states = {rm["name"]: rm for rm in payload["read_models"]}
    assert rm_states["site_index"]["exists"] is True
    assert rm_states["site_index"]["schema_version"] == 1


def test_sources_list_and_detail(
    client: TestClient,
    initialized_vault: VaultPaths,
) -> None:
    with connect(initialized_vault.registry_db) as conn:
        source = capture_note("S-Source", why_interesting="x", conn=conn, paths=initialized_vault)
    listing = client.get("/api/sources").json()
    assert listing["count"] >= 1
    detail = client.get(f"/api/sources/{source.id}").json()
    assert detail["id"] == source.id
    assert "sha256" in detail


def test_sources_detail_404(client: TestClient) -> None:
    assert client.get("/api/sources/src_does_not_exist").status_code == 404


def test_freshness_volatile_via_pages_after_publish(
    client: TestClient,
    initialized_vault: VaultPaths,
) -> None:
    """Direkter PageRepository-Insert mit overdue review_after; danach Pages-Detail."""
    with connect(initialized_vault.registry_db) as conn:
        repo = PageRepository(conn)
        now = datetime.now(tz=UTC)
        page = Page(
            id="page_FRESHTEST",
            title="Fresh Test",
            slug="fresh-test",
            page_type=PageType.PRODUCT_RESEARCH,
            status=PageStatus.ACTIVE,
            freshness=Freshness.VOLATILE,
            confidence=ConfidenceLevel.MEDIUM,
            created_at=now,
            updated_at=now,
            review_after=now - timedelta(days=5),
            sources=[],
            why_interesting="x",
        )
        repo.insert(page)
    response = client.get("/api/pages/page_FRESHTEST")
    assert response.status_code == 200
    payload = response.json()
    assert payload["review_after"] is not None


def test_search_empty_query_returns_empty(client: TestClient) -> None:
    """Empty query gives 0 results without error."""
    response = client.get("/api/search?q=")
    assert response.status_code == 200
    assert response.json()["count"] == 0


def test_proposals_detail_404(client: TestClient) -> None:
    assert client.get("/api/proposals/prop_does_not_exist").status_code == 404


_ = yaml  # avoid unused-import warning if monkey doesn't use it later
