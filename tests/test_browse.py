"""M4 Tests: Browse-Lesepfade (random, topic, collection)."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

import pytest

from curiosity_wiki.browse import browse_by_collection, browse_by_topic, browse_random
from curiosity_wiki.paths import VaultPaths
from curiosity_wiki.registry import connect, migrate
from curiosity_wiki.wiki.models import (
    ConfidenceLevel,
    Freshness,
    Page,
    PageStatus,
    PageType,
)
from curiosity_wiki.wiki.repository import LinkRepository, PageRepository


@pytest.fixture
def vault(tmp_path: Path) -> VaultPaths:
    (tmp_path / "pyproject.toml").write_text("[project]\nname='dummy'\n", encoding="utf-8")
    return VaultPaths(root=tmp_path)


@pytest.fixture
def conn(vault: VaultPaths) -> Iterator:
    with connect(vault.registry_db) as connection:
        migrate(connection)
        yield connection


def _make_page(
    repo: PageRepository,
    *,
    page_id: str,
    title: str,
    slug: str,
    page_type: PageType,
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
        why_interesting="test",
        llm_generated=False,
        human_reviewed=True,
        reviewed_at=now,
    )
    repo.insert(page)
    return page


def test_browse_random_excludes_source_pages(conn) -> None:
    repo = PageRepository(conn)
    _make_page(repo, page_id="page_TOPIC", title="Topic", slug="topic", page_type=PageType.TOPIC)
    _make_page(
        repo, page_id="page_SOURCE", title="Source", slug="source", page_type=PageType.SOURCE
    )
    entries = browse_random(conn, limit=10)
    types = {e.page_type for e in entries}
    assert "source" not in types
    assert "topic" in types


def test_browse_topic_via_backlinks(conn) -> None:
    """Pages, die zu einer Topic-Page verlinken, werden gefunden."""
    repo = PageRepository(conn)
    topic = _make_page(
        repo, page_id="page_TUNESCO", title="UNESCO", slug="unesco", page_type=PageType.TOPIC
    )
    place = _make_page(
        repo,
        page_id="page_PLALHAMBRA",
        title="Alhambra",
        slug="alhambra",
        page_type=PageType.PLACE,
    )
    LinkRepository(conn).insert(
        from_page_id=place.id,
        to_page_id=topic.id,
        target_text="UNESCO",
        status="resolved",
    )
    entries = browse_by_topic(conn, "UNESCO")
    assert any(e.page_id == place.id for e in entries)


def test_browse_topic_fallback_substring(conn) -> None:
    """Wenn keine Topic-Page existiert, wird LIKE-Fallback verwendet."""
    repo = PageRepository(conn)
    _make_page(
        repo,
        page_id="page_PALH",
        title="Alhambra in Granada",
        slug="alhambra",
        page_type=PageType.PLACE,
    )
    entries = browse_by_topic(conn, "Alhambra")
    assert any(e.title.startswith("Alhambra") for e in entries)


def test_browse_collection_via_outgoing_links(conn) -> None:
    """Collection-Page mit Wikilinks: Browse listet die Ziele."""
    repo = PageRepository(conn)
    coll = _make_page(
        repo,
        page_id="page_CFOO",
        title="Foo Picks",
        slug="foo-picks",
        page_type=PageType.COLLECTION,
    )
    target = _make_page(
        repo,
        page_id="page_TOPI1",
        title="Topic One",
        slug="topic-one",
        page_type=PageType.TOPIC,
    )
    LinkRepository(conn).insert(
        from_page_id=coll.id,
        to_page_id=target.id,
        target_text="Topic One",
        status="resolved",
    )
    entries = browse_by_collection(conn, "Foo Picks")
    assert [e.page_id for e in entries] == [target.id]


def test_browse_collection_unknown_returns_empty(conn) -> None:
    assert browse_by_collection(conn, "Definitely-Missing") == []
