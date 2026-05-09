"""M5 Tests: HTML-Views (Jinja2 + Templates)."""

from __future__ import annotations

import shutil
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from curiosity_wiki.config import CuriosityConfig
from curiosity_wiki.extraction import extract_source
from curiosity_wiki.paths import VaultPaths, get_paths
from curiosity_wiki.proposals import ingest_source
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


def _make_page_with_md(
    vault: VaultPaths,
    *,
    page_id: str,
    title: str,
    slug: str,
    body: str = "Some body content.",
    page_type: PageType = PageType.TOPIC,
) -> Page:
    now = datetime.now(tz=UTC)
    page = Page(
        id=page_id,
        title=title,
        slug=slug,
        page_type=page_type,
        status=PageStatus.ACTIVE,
        freshness=Freshness.STABLE,
        confidence=ConfidenceLevel.MEDIUM,
        created_at=now,
        updated_at=now,
        sources=[],
        why_interesting="why",
        llm_generated=False,
        human_reviewed=True,
        reviewed_at=now,
    )
    front = render_frontmatter(page)
    target = vault.root / page.relative_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(front + "\n# " + title + "\n\n" + body, encoding="utf-8")
    return page


def test_home_renders_html(client: TestClient) -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Curiosity Wiki" in response.text
    assert "Heute interessant" in response.text


def test_home_shows_random_walk_pages(client: TestClient, initialized_vault: VaultPaths) -> None:
    with connect(initialized_vault.registry_db) as conn:
        page = _make_page_with_md(
            initialized_vault,
            page_id="page_HOMERND",
            title="Random Test Page",
            slug="random-test-page",
        )
        PageRepository(conn).insert(page)
    response = client.get("/")
    assert "Random Test Page" in response.text


def test_page_view_renders_body_and_backlinks(
    client: TestClient, initialized_vault: VaultPaths
) -> None:
    with connect(initialized_vault.registry_db) as conn:
        repo = PageRepository(conn)
        target = _make_page_with_md(
            initialized_vault,
            page_id="page_VTARG",
            title="View Target",
            slug="view-target",
            body="This is the body content with details.",
        )
        caller = _make_page_with_md(
            initialized_vault,
            page_id="page_VCALL",
            title="View Caller",
            slug="view-caller",
            body="Sees [[View Target]].",
        )
        repo.insert(target)
        repo.insert(caller)
        LinkRepository(conn).insert(
            from_page_id=caller.id,
            to_page_id=target.id,
            target_text="View Target",
            status="resolved",
        )
    response = client.get("/p/view-target")
    assert response.status_code == 200
    assert "View Target" in response.text
    assert "body content with details" in response.text
    # Backlinks-Sektion nennt Caller
    assert "View Caller" in response.text


def test_page_view_resolves_wikilinks_to_anchor(
    client: TestClient, initialized_vault: VaultPaths
) -> None:
    with connect(initialized_vault.registry_db) as conn:
        repo = PageRepository(conn)
        target = _make_page_with_md(
            initialized_vault,
            page_id="page_WLT",
            title="Linked Page",
            slug="linked-page",
            body="Target body.",
        )
        caller = _make_page_with_md(
            initialized_vault,
            page_id="page_WLC",
            title="Caller",
            slug="caller-2",
            body="Refers to [[Linked Page]] inline.",
        )
        repo.insert(target)
        repo.insert(caller)
    response = client.get("/p/caller-2")
    assert response.status_code == 200
    # Wikilink wurde zu /p/linked-page aufgeloest
    assert 'href="/p/linked-page"' in response.text
    assert "[[Linked Page]]" not in response.text  # resolved away


def test_page_view_broken_wikilink_marked(
    client: TestClient, initialized_vault: VaultPaths
) -> None:
    with connect(initialized_vault.registry_db) as conn:
        page = _make_page_with_md(
            initialized_vault,
            page_id="page_BWL",
            title="Has Broken Link",
            slug="has-broken-link",
            body="Refers to [[Definitely Missing]].",
        )
        PageRepository(conn).insert(page)
    response = client.get("/p/has-broken-link")
    assert response.status_code == 200
    assert "broken-link" in response.text
    assert "Definitely Missing" in response.text


def test_page_view_404(client: TestClient) -> None:
    assert client.get("/p/no-such-slug").status_code == 404


def test_search_view_empty_q(client: TestClient) -> None:
    response = client.get("/search")
    assert response.status_code == 200
    # Form ist da, keine Ergebnisse
    assert 'name="q"' in response.text or 'name="q"' in response.text


def test_search_view_with_query(
    client: TestClient,
    initialized_vault: VaultPaths,
    mock_config: CuriosityConfig,
) -> None:
    """Mock-Provider produziert 'Mock Topic' — Search-View zeigt's."""
    with connect(initialized_vault.registry_db) as conn:
        source = capture_note(
            "View-Source", why_interesting="x", conn=conn, paths=initialized_vault
        )
        extract_source(source.id, conn=conn, paths=initialized_vault)
        result = ingest_source(source.id, conn=conn, paths=initialized_vault, config=mock_config)
        publish_proposal(result.proposal_id, conn=conn, paths=initialized_vault, auto_commit=False)
    response = client.get("/search?q=Mock")
    assert response.status_code == 200
    assert "Mock Topic" in response.text


def test_source_view_renders(client: TestClient, initialized_vault: VaultPaths) -> None:
    with connect(initialized_vault.registry_db) as conn:
        source = capture_note(
            "Source View Note",
            why_interesting="testing source view",
            conn=conn,
            paths=initialized_vault,
        )
    response = client.get(f"/s/{source.id}")
    assert response.status_code == 200
    assert "Source View Note" in response.text
    assert "testing source view" in response.text
    assert source.id in response.text


def test_source_view_404(client: TestClient) -> None:
    assert client.get("/s/src_nonexistent").status_code == 404


def test_static_css_served(client: TestClient) -> None:
    response = client.get("/static/css/main.css")
    assert response.status_code == 200
    assert "text/css" in response.headers["content-type"]
    assert "Curiosity Wiki" in response.text  # Header-Kommentar


def test_home_has_skip_link_and_main_landmark(client: TestClient) -> None:
    """Accessibility-Basics: skip-link + main-Element."""
    response = client.get("/")
    assert response.status_code == 200
    assert 'class="skip-link"' in response.text
    assert "<main" in response.text
    assert 'role="main"' in response.text
