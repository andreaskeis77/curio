"""M5 Tests: Read-Model-Builder (ADR-0016)."""

from __future__ import annotations

import json
import shutil
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
import yaml

from curiosity_wiki.config import CuriosityConfig
from curiosity_wiki.extraction import extract_source
from curiosity_wiki.paths import VaultPaths, get_paths
from curiosity_wiki.proposals import ingest_source
from curiosity_wiki.read_models import (
    READ_MODEL_FILES,
    READ_MODEL_SCHEMA_VERSION,
    read_model_status,
    rebuild_all,
)
from curiosity_wiki.registry import connect, migrate
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


def _write_md_page(
    vault: VaultPaths,
    *,
    page_type: PageType,
    slug: str,
    title: str,
    body: str = "Some body content for excerpt extraction.",
    open_questions: list[str] | None = None,
) -> Page:
    now = datetime.now(tz=UTC)
    page = Page(
        id="page_TESTRM" + slug.upper().replace("-", ""),
        title=title,
        slug=slug,
        page_type=page_type,
        status=PageStatus.ACTIVE,
        freshness=Freshness.STABLE,
        confidence=ConfidenceLevel.MEDIUM,
        created_at=now,
        updated_at=now,
        sources=[],
        why_interesting=f"why {slug}",
        llm_generated=False,
        human_reviewed=True,
        reviewed_at=now,
        tags=["sample", "rm-test"],
    )
    front = render_frontmatter(page)
    if open_questions:
        block = "open_questions:\n" + "\n".join(f"- {q}" for q in open_questions) + "\n"
        front = front.replace("---\n", "---\n" + block, 1)
    target = vault.root / page.relative_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(front + "\n# " + title + "\n\n" + body, encoding="utf-8")
    return page


def test_rebuild_all_writes_all_models(vault: VaultPaths, conn) -> None:
    """Rebuild schreibt alle 7 Read-Models."""
    page = _write_md_page(vault, page_type=PageType.TOPIC, slug="alhambra", title="Alhambra")
    PageRepository(conn).insert(page)
    result = rebuild_all(conn, paths=vault)
    written = {Path(p).name for p in result.written}
    expected = set(READ_MODEL_FILES.values())
    assert expected.issubset(written), f"missing: {expected - written}"
    assert result.skipped == []


def test_site_index_contains_active_pages(vault: VaultPaths, conn) -> None:
    page = _write_md_page(vault, page_type=PageType.TOPIC, slug="alhambra", title="Alhambra")
    PageRepository(conn).insert(page)
    rebuild_all(conn, paths=vault)
    site_index = json.loads(
        (vault.read_models / READ_MODEL_FILES["site_index"]).read_text(encoding="utf-8")
    )
    assert site_index["meta"]["schema_version"] == READ_MODEL_SCHEMA_VERSION
    titles = {entry["title"] for entry in site_index["data"]}
    assert "Alhambra" in titles


def test_graph_includes_links(vault: VaultPaths, conn) -> None:
    """links-Tabelle landet als Edges im Graph."""
    repo = PageRepository(conn)
    a = _write_md_page(vault, page_type=PageType.TOPIC, slug="a", title="Alpha")
    b = _write_md_page(vault, page_type=PageType.TOPIC, slug="b", title="Beta")
    repo.insert(a)
    repo.insert(b)
    LinkRepository(conn).insert(
        from_page_id=a.id, to_page_id=b.id, target_text="Beta", status="resolved"
    )
    rebuild_all(conn, paths=vault)
    graph = json.loads((vault.read_models / READ_MODEL_FILES["graph"]).read_text(encoding="utf-8"))
    edges = graph["data"]["edges"]
    assert any(e["from"] == a.id and e["to"] == b.id for e in edges)


def test_freshness_dashboard_buckets(vault: VaultPaths, conn) -> None:
    """Overdue Page landet im freshness_dashboard."""
    repo = PageRepository(conn)
    now = datetime.now(tz=UTC)
    overdue = Page(
        id="page_OVERDUE_RM",
        title="Overdue",
        slug="overdue",
        page_type=PageType.PRODUCT_RESEARCH,
        status=PageStatus.ACTIVE,
        freshness=Freshness.VOLATILE,
        confidence=ConfidenceLevel.MEDIUM,
        created_at=now,
        updated_at=now,
        review_after=now - timedelta(days=14),
        sources=[],
        why_interesting="x",
    )
    repo.insert(overdue)
    rebuild_all(conn, paths=vault)
    dash = json.loads(
        (vault.read_models / READ_MODEL_FILES["freshness_dashboard"]).read_text(encoding="utf-8")
    )
    overdue_ids = {entry["page_id"] for entry in dash["data"]["overdue"]}
    assert "page_OVERDUE_RM" in overdue_ids


def test_page_cards_include_backlink_count(vault: VaultPaths, conn) -> None:
    repo = PageRepository(conn)
    a = _write_md_page(vault, page_type=PageType.TOPIC, slug="ca", title="CardA")
    b = _write_md_page(vault, page_type=PageType.TOPIC, slug="cb", title="CardB")
    repo.insert(a)
    repo.insert(b)
    LinkRepository(conn).insert(
        from_page_id=a.id, to_page_id=b.id, target_text="CardB", status="resolved"
    )
    rebuild_all(conn, paths=vault)
    cards = json.loads(
        (vault.read_models / READ_MODEL_FILES["page_cards"]).read_text(encoding="utf-8")
    )
    by_id = {card["id"]: card for card in cards["data"]}
    assert by_id[b.id]["backlink_count"] >= 1
    assert by_id[a.id]["backlink_count"] == 0


def test_search_documents_jsonl_one_per_page(vault: VaultPaths, conn) -> None:
    a = _write_md_page(vault, page_type=PageType.TOPIC, slug="sd1", title="Doc One")
    b = _write_md_page(vault, page_type=PageType.TOPIC, slug="sd2", title="Doc Two")
    repo = PageRepository(conn)
    repo.insert(a)
    repo.insert(b)
    rebuild_all(conn, paths=vault)
    text = (vault.read_models / READ_MODEL_FILES["search_documents"]).read_text(encoding="utf-8")
    lines = [line for line in text.splitlines() if line.strip()]
    assert len(lines) == 2
    docs = [json.loads(line) for line in lines]
    titles = {doc["title"] for doc in docs}
    assert titles == {"Doc One", "Doc Two"}
    assert all("body_excerpt" in doc for doc in docs)


def test_open_questions_read_model(vault: VaultPaths, conn) -> None:
    _write_md_page(
        vault,
        page_type=PageType.TOPIC,
        slug="alh",
        title="Alhambra",
        open_questions=["Wann genau?", "Welche Restaurierungen?"],
    )
    rebuild_all(conn, paths=vault)
    payload = json.loads(
        (vault.read_models / READ_MODEL_FILES["open_questions"]).read_text(encoding="utf-8")
    )
    questions = [item["text"] for item in payload["data"]]
    assert "Wann genau?" in questions


def test_mobile_nav_lists_topics_and_collections(vault: VaultPaths, conn) -> None:
    repo = PageRepository(conn)
    repo.insert(_write_md_page(vault, page_type=PageType.TOPIC, slug="topic-x", title="Topic X"))
    repo.insert(_write_md_page(vault, page_type=PageType.COLLECTION, slug="coll-x", title="Coll X"))
    rebuild_all(conn, paths=vault)
    nav = json.loads(
        (vault.read_models / READ_MODEL_FILES["mobile_nav"]).read_text(encoding="utf-8")
    )
    topic_titles = {t["title"] for t in nav["data"]["topics"]}
    coll_titles = {c["title"] for c in nav["data"]["collections"]}
    assert "Topic X" in topic_titles
    assert "Coll X" in coll_titles


def test_read_model_status_after_rebuild(vault: VaultPaths, conn) -> None:
    rebuild_all(conn, paths=vault)
    statuses = {s.name: s for s in read_model_status(paths=vault)}
    assert statuses["site_index"].exists
    assert statuses["site_index"].schema_version == READ_MODEL_SCHEMA_VERSION
    assert statuses["site_index"].built_at is not None
    # JSONL hat keinen meta-Header — exists ja, schema_version None.
    assert statuses["search_documents"].exists
    assert statuses["search_documents"].schema_version is None


def test_rebuild_after_publish_includes_published_page(
    vault: VaultPaths,
    conn,
    mock_config: CuriosityConfig,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """End-to-end: publish liefert eine Page, Rebuild bringt sie ins site_index."""
    monkeypatch.setenv("CURIOSITY_VAULT_ROOT", str(vault.root))
    source = capture_note("RM-Source", why_interesting="rm-test", conn=conn, paths=vault)
    extract_source(source.id, conn=conn, paths=vault)
    fixture_dir = vault.tests_fixtures / "llm_outputs" / "ingest_v0_1"
    fixture_dir.mkdir(parents=True, exist_ok=True)
    (fixture_dir / f"{source.id}.yaml").write_text(
        yaml.safe_dump(
            {
                "new_pages": [
                    {
                        "title": "RM Smoke",
                        "slug": "rm-smoke",
                        "type": "topic",
                        "sources": [source.id],
                        "sections": [{"heading": "Kurzfassung", "markdown": "Ein kurzer Body."}],
                        "open_questions": [],
                        "why_interesting": "rm",
                        "confidence": "medium",
                    }
                ],
                "hard_facts": [],
                "open_questions": [],
                "risk_notes": [],
                "freshness_recommendations": [{"page_title": "RM Smoke", "freshness": "stable"}],
                "overall_confidence": "medium",
                "summary": "rm",
            },
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    ingest_result = ingest_source(source.id, conn=conn, paths=vault, config=mock_config)
    publish_proposal(ingest_result.proposal_id, conn=conn, paths=vault, auto_commit=False)
    rebuild_all(conn, paths=vault)
    site_index = json.loads(
        (vault.read_models / READ_MODEL_FILES["site_index"]).read_text(encoding="utf-8")
    )
    titles = {entry["title"] for entry in site_index["data"]}
    assert "RM Smoke" in titles
