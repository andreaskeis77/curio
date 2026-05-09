"""M4 Tests: FTS5-Suche und Index-Rebuild (ADR-0014)."""

from __future__ import annotations

import shutil
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

import pytest
import yaml

from curiosity_wiki.config import CuriosityConfig
from curiosity_wiki.extraction import extract_source
from curiosity_wiki.paths import VaultPaths, get_paths
from curiosity_wiki.proposals import ingest_source
from curiosity_wiki.registry import connect, migrate
from curiosity_wiki.search import (
    SearchError,
    index_page,
    rebuild_index_from_markdown,
    search_pages,
)
from curiosity_wiki.sources import capture_note
from curiosity_wiki.wiki import publish_proposal
from curiosity_wiki.wiki.frontmatter import render_frontmatter
from curiosity_wiki.wiki.models import (
    ConfidenceLevel,
    Freshness,
    Page,
    PageStatus,
    PageType,
)
from curiosity_wiki.wiki.repository import PageRepository


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


def _make_published_page(
    vault: VaultPaths,
    conn,
    config: CuriosityConfig,
    monkeypatch: pytest.MonkeyPatch,
    *,
    title: str,
    slug: str,
    body_markdown: str,
    page_type: str = "topic",
) -> str:
    monkeypatch.setenv("CURIOSITY_VAULT_ROOT", str(vault.root))
    source = capture_note(f"Source-{slug}", why_interesting="x", conn=conn, paths=vault)
    extract_source(source.id, conn=conn, paths=vault)
    fixture_dir = vault.tests_fixtures / "llm_outputs" / "ingest_v0_1"
    fixture_dir.mkdir(parents=True, exist_ok=True)
    fixture = {
        "new_pages": [
            {
                "title": title,
                "slug": slug,
                "type": page_type,
                "sources": [source.id],
                "sections": [{"heading": "Kurzfassung", "markdown": body_markdown}],
                "open_questions": [],
                "why_interesting": f"why {slug}",
                "confidence": "medium",
            }
        ],
        "hard_facts": [],
        "open_questions": [],
        "risk_notes": [],
        "freshness_recommendations": [{"page_title": title, "freshness": "stable"}],
        "overall_confidence": "medium",
        "summary": "search test",
    }
    (fixture_dir / f"{source.id}.yaml").write_text(
        yaml.safe_dump(fixture, allow_unicode=True), encoding="utf-8"
    )
    ingest_result = ingest_source(source.id, conn=conn, paths=vault, config=config)
    assert ingest_result.proposal_id is not None
    publish_proposal(ingest_result.proposal_id, conn=conn, paths=vault, auto_commit=False)
    page = next(p for p in PageRepository(conn).list_all() if p.title == title)
    return page.id


def test_publish_indexes_page_in_fts(
    vault: VaultPaths,
    conn,
    mock_config: CuriosityConfig,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Nach publish_proposal hat pages_fts mindestens eine row pro Page."""
    page_id = _make_published_page(
        vault,
        conn,
        mock_config,
        monkeypatch,
        title="Alhambra",
        slug="alhambra",
        body_markdown="Eine maurische Festungsanlage in Granada.",
    )
    rows = conn.execute(
        "SELECT page_id, title FROM pages_fts WHERE page_id = ?", (page_id,)
    ).fetchall()
    assert rows, f"page {page_id} not in pages_fts after publish"


def test_search_finds_published_page_by_body(
    vault: VaultPaths,
    conn,
    mock_config: CuriosityConfig,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _make_published_page(
        vault,
        conn,
        mock_config,
        monkeypatch,
        title="Alhambra",
        slug="alhambra",
        body_markdown="Eine maurische Festungsanlage in Granada.",
    )
    hits = search_pages(conn, "maurische")
    titles = [h.title for h in hits]
    assert "Alhambra" in titles


def test_search_filters_by_type(
    vault: VaultPaths,
    conn,
    mock_config: CuriosityConfig,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _make_published_page(
        vault,
        conn,
        mock_config,
        monkeypatch,
        title="Pacojet",
        slug="pacojet",
        body_markdown="Kuechengeraet zur Herstellung von tiefgekuehlten Pasten.",
        page_type="method",
    )
    hits_topic = search_pages(conn, "Pasten", page_type="topic")
    hits_method = search_pages(conn, "Pasten", page_type="method")
    assert all(h.page_type == "method" for h in hits_method)
    assert "Pacojet" not in [h.title for h in hits_topic]
    assert "Pacojet" in [h.title for h in hits_method]


def test_search_returns_empty_for_no_match(
    vault: VaultPaths,
    conn,
    mock_config: CuriosityConfig,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _make_published_page(
        vault,
        conn,
        mock_config,
        monkeypatch,
        title="Alhambra",
        slug="alhambra",
        body_markdown="Maurische Festung in Granada.",
    )
    assert search_pages(conn, "raumschiff") == []


def test_search_diacritics_insensitive(
    vault: VaultPaths,
    conn,
    mock_config: CuriosityConfig,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """unicode61 remove_diacritics 1: Stätte wird zu Statte tokenisiert."""
    _make_published_page(
        vault,
        conn,
        mock_config,
        monkeypatch,
        title="Alhambra",
        slug="alhambra",
        body_markdown="Die Stätte wurde aufgenommen.",
    )
    # Suche ohne Akzent findet die Page mit Akzent.
    hits = search_pages(conn, "Statte")
    assert any(h.title == "Alhambra" for h in hits)


def test_search_invalid_filter_raises(
    vault: VaultPaths,
    conn,
    mock_config: CuriosityConfig,
) -> None:
    with pytest.raises(SearchError):
        search_pages(conn, "x", page_type="not-a-type")


def _write_wiki_md(
    vault: VaultPaths,
    *,
    page_type: PageType,
    slug: str,
    title: str,
    body_extra: str = "",
) -> Path:
    now = datetime.now(tz=UTC)
    page = Page(
        id="page_TESTREBUILD" + slug.upper().replace("-", ""),
        title=title,
        slug=slug,
        page_type=page_type,
        status=PageStatus.ACTIVE,
        freshness=Freshness.STABLE,
        confidence=ConfidenceLevel.MEDIUM,
        created_at=now,
        updated_at=now,
        last_checked=now,
        sources=["src_test"],
        why_interesting="rebuild test",
        llm_generated=False,
        human_reviewed=True,
        reviewed_at=now,
    )
    front = render_frontmatter(page)
    body = f"# {title}\n\n_(content)_\n{body_extra}"
    target = vault.root / page.relative_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(front + "\n" + body, encoding="utf-8")
    return target


def test_index_rebuild_populates_fts_from_markdown(vault: VaultPaths, conn) -> None:
    """Rebuild aus Wiki-Markdown ist die Wahrheit (siehe ADR-0014)."""
    _write_wiki_md(
        vault,
        page_type=PageType.TOPIC,
        slug="alhambra",
        title="Alhambra",
        body_extra="\n\nDie Stätte ist beruehmt fuer ihre Architektur.\n",
    )
    result = rebuild_index_from_markdown(conn, paths=vault)
    assert result.files_scanned == 1
    assert result.rows_written == 1
    rows = conn.execute("SELECT title FROM pages_fts").fetchall()
    assert any(row["title"] == "Alhambra" for row in rows)


def test_index_rebuild_clears_old_entries(vault: VaultPaths, conn) -> None:
    """Rebuild ist ein DELETE+INSERT, alte Eintraege fuer entfernte Files verschwinden."""
    index_page(
        conn,
        page_id="page_GHOST",
        title="Ghost",
        body="not on disk anymore",
    )
    rebuild_index_from_markdown(conn, paths=vault)
    rows = conn.execute(
        "SELECT page_id FROM pages_fts WHERE page_id = ?", ("page_GHOST",)
    ).fetchall()
    assert rows == []
