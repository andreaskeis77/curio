"""M4 Tests: Backlinks-Auto-Compute beim Publish (links-Tabelle)."""

from __future__ import annotations

import shutil
from collections.abc import Iterator
from pathlib import Path

import pytest
import yaml

from curiosity_wiki.config import CuriosityConfig
from curiosity_wiki.extraction import extract_source
from curiosity_wiki.paths import VaultPaths, get_paths
from curiosity_wiki.proposals import ingest_source
from curiosity_wiki.registry import connect, migrate
from curiosity_wiki.sources import capture_note
from curiosity_wiki.wiki import publish_proposal
from curiosity_wiki.wiki.repository import LinkRepository, PageRepository


@pytest.fixture
def vault(tmp_path: Path) -> VaultPaths:
    (tmp_path / "pyproject.toml").write_text("[project]\nname='dummy'\n", encoding="utf-8")
    real = get_paths().prompts
    if real.exists():
        shutil.copytree(real, tmp_path / "prompts")
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


def _publish_with_fixture(
    vault: VaultPaths,
    conn,
    config: CuriosityConfig,
    monkeypatch: pytest.MonkeyPatch,
    *,
    body_markdown: str,
    title: str = "Linked Page",
    slug: str = "linked-page",
) -> str:
    """Capture -> Extract -> Ingest mit eigener Fixture -> Publish. Returns page_id."""
    monkeypatch.setenv("CURIOSITY_VAULT_ROOT", str(vault.root))
    source = capture_note("Link-Test-Source", why_interesting="x", conn=conn, paths=vault)
    extract_source(source.id, conn=conn, paths=vault)
    fixture_dir = vault.tests_fixtures / "llm_outputs" / "ingest_v0_1"
    fixture_dir.mkdir(parents=True, exist_ok=True)
    fixture = {
        "new_pages": [
            {
                "title": title,
                "slug": slug,
                "type": "topic",
                "sources": [source.id],
                "sections": [{"heading": "Kurzfassung", "markdown": body_markdown}],
                "open_questions": [],
                "why_interesting": "links test",
                "confidence": "medium",
            }
        ],
        "hard_facts": [],
        "open_questions": [],
        "risk_notes": [],
        "freshness_recommendations": [{"page_title": title, "freshness": "stable"}],
        "overall_confidence": "medium",
        "summary": "links test",
    }
    (fixture_dir / f"{source.id}.yaml").write_text(
        yaml.safe_dump(fixture, allow_unicode=True), encoding="utf-8"
    )
    ingest_result = ingest_source(source.id, conn=conn, paths=vault, config=config)
    assert ingest_result.proposal_id is not None
    publish_proposal(ingest_result.proposal_id, conn=conn, paths=vault, auto_commit=False)
    page_repo = PageRepository(conn)
    pages = [p for p in page_repo.list_all() if p.title == title]
    assert pages, f"page {title!r} not in registry after publish"
    return pages[0].id


def test_publish_writes_broken_wikilink_to_links_table(
    vault: VaultPaths,
    conn,
    mock_config: CuriosityConfig,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """[[Unknown Target]] -> links-row mit status='broken', to_page_id=NULL."""
    page_id = _publish_with_fixture(
        vault,
        conn,
        mock_config,
        monkeypatch,
        body_markdown="Verknuepft mit [[Unknown Target]] zur Demo.",
    )
    rows = LinkRepository(conn).broken_links()
    assert any(
        row["from_page_id"] == page_id and row["target_text"] == "Unknown Target" for row in rows
    ), f"expected broken link from {page_id} to 'Unknown Target' in links table"


def test_publish_resolves_wikilink_to_existing_page(
    vault: VaultPaths,
    conn,
    mock_config: CuriosityConfig,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Wikilink auf eine im selben Publish erzeugte Source-Page wird resolved."""
    # Source-Page-Title wird aus source.title abgeleitet ("Link-Test-Source")
    page_id = _publish_with_fixture(
        vault,
        conn,
        mock_config,
        monkeypatch,
        body_markdown="Siehe [[Link-Test-Source]] fuer Hintergrund.",
    )
    # Mindestens ein resolved-Link erwartet (Body referenziert Source-Page-Titel).
    rows = conn.execute(
        "SELECT to_page_id, status, target_text FROM links WHERE from_page_id = ?",
        (page_id,),
    ).fetchall()
    resolved = [r for r in rows if r["status"] == "resolved"]
    assert resolved, f"expected at least one resolved link, got {[dict(r) for r in rows]}"


def test_publish_backlinks_query_returns_caller_page(
    vault: VaultPaths,
    conn,
    mock_config: CuriosityConfig,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """LinkRepository.backlinks(target_id) liefert from_page_id der verlinkenden Page."""
    caller_id = _publish_with_fixture(
        vault,
        conn,
        mock_config,
        monkeypatch,
        body_markdown="Quelle: [[Link-Test-Source]].",
    )
    page_repo = PageRepository(conn)
    target = next(p for p in page_repo.list_all() if p.title.lower() == "link-test-source")
    backlinks = LinkRepository(conn).backlinks(target.id)
    assert caller_id in backlinks
