"""M4 Tests: Open-Questions- und Freshness-Aggregation."""

from __future__ import annotations

import shutil
from collections.abc import Iterator
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pytest

from curiosity_wiki.paths import VaultPaths, get_paths
from curiosity_wiki.registry import connect, migrate
from curiosity_wiki.wiki.aggregations import (
    collect_freshness_status,
    collect_open_questions,
)
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


def _write_page_md(
    vault: VaultPaths,
    *,
    page_type: PageType,
    slug: str,
    title: str,
    body: str = "",
    open_questions: list[str] | None = None,
) -> Path:
    now = datetime.now(tz=UTC)
    page = Page(
        id="page_TESTAGG" + slug.upper().replace("-", ""),
        title=title,
        slug=slug,
        page_type=page_type,
        status=PageStatus.ACTIVE,
        freshness=Freshness.STABLE,
        confidence=ConfidenceLevel.MEDIUM,
        created_at=now,
        updated_at=now,
        sources=[],
        why_interesting="agg test",
        llm_generated=False,
        human_reviewed=True,
        reviewed_at=now,
    )
    front_text = render_frontmatter(page)
    if open_questions:
        # open_questions ins YAML einfuegen
        block = "open_questions:\n" + "\n".join(f"- {q}" for q in open_questions) + "\n"
        front_text = front_text.replace("---\n", "---\n" + block, 1)
    target = vault.root / page.relative_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(front_text + "\n" + body, encoding="utf-8")
    return target


def test_open_questions_from_question_pages_and_frontmatter(vault: VaultPaths) -> None:
    _write_page_md(
        vault,
        page_type=PageType.QUESTION,
        slug="warum-pacojet",
        title="Warum ist der Pacojet so teuer?",
    )
    _write_page_md(
        vault,
        page_type=PageType.TOPIC,
        slug="alhambra",
        title="Alhambra",
        open_questions=["Was ist die genaue Erstdatierung?", "Welche Restaurierungen gab es?"],
    )
    items = collect_open_questions(paths=vault)
    sources = {item.source for item in items}
    assert "question_page" in sources
    assert "frontmatter" in sources
    assert any("Pacojet" in item.text and item.source == "question_page" for item in items)
    assert sum(1 for item in items if item.source == "frontmatter") == 2


def test_freshness_overdue_and_volatile(vault: VaultPaths, conn) -> None:
    repo = PageRepository(conn)
    now = datetime.now(tz=UTC)
    # Overdue page
    overdue = Page(
        id="page_OVERDUE",
        title="Overdue",
        slug="overdue",
        page_type=PageType.PRODUCT_RESEARCH,
        status=PageStatus.ACTIVE,
        freshness=Freshness.VOLATILE,
        confidence=ConfidenceLevel.MEDIUM,
        created_at=now,
        updated_at=now,
        review_after=now - timedelta(days=10),
        sources=[],
        why_interesting="x",
    )
    repo.insert(overdue)
    # Volatile without schedule
    vol = Page(
        id="page_VOL",
        title="Volatile",
        slug="vol",
        page_type=PageType.TOPIC,
        status=PageStatus.ACTIVE,
        freshness=Freshness.VOLATILE,
        confidence=ConfidenceLevel.MEDIUM,
        created_at=now,
        updated_at=now,
        sources=[],
        why_interesting="x",
    )
    repo.insert(vol)
    report = collect_freshness_status(conn, today=date.today())
    overdue_ids = {e.page_id for e in report.overdue}
    vol_ids = {e.page_id for e in report.volatile_without_schedule}
    assert "page_OVERDUE" in overdue_ids
    assert "page_VOL" in vol_ids


def test_freshness_due_within_7_days(vault: VaultPaths, conn) -> None:
    repo = PageRepository(conn)
    now = datetime.now(tz=UTC)
    soon = Page(
        id="page_SOON",
        title="Soon",
        slug="soon",
        page_type=PageType.PRODUCT_RESEARCH,
        status=PageStatus.ACTIVE,
        freshness=Freshness.PERIODIC,
        confidence=ConfidenceLevel.MEDIUM,
        created_at=now,
        updated_at=now,
        review_after=now + timedelta(days=3),
        sources=[],
        why_interesting="x",
    )
    repo.insert(soon)
    report = collect_freshness_status(conn, today=date.today())
    assert any(e.page_id == "page_SOON" for e in report.due_within_7_days)
