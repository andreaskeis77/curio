"""Tests fuer das Lint-Modul (M3 Basisregeln)."""

from __future__ import annotations

import shutil
from collections.abc import Iterator
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pytest

from curiosity_wiki.linting import run_lint
from curiosity_wiki.paths import VaultPaths, get_paths
from curiosity_wiki.registry import connect, migrate
from curiosity_wiki.wiki.frontmatter import render_frontmatter
from curiosity_wiki.wiki.models import (
    ConfidenceLevel,
    Freshness,
    Page,
    PageStatus,
    PageType,
)


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


def _write_page(
    vault: VaultPaths,
    *,
    page_type: PageType,
    slug: str,
    title: str,
    sources: list[str] | None = None,
    body_extra: str = "",
    freshness: Freshness = Freshness.STABLE,
    review_after_days: int | None = None,
) -> Path:
    now = datetime.now(tz=UTC)
    review_after: datetime | None = None
    if review_after_days is not None:
        review_after = now + timedelta(days=review_after_days)
    page = Page(
        id="page_TEST" + slug.upper().replace("-", ""),
        title=title,
        slug=slug,
        page_type=page_type,
        status=PageStatus.ACTIVE,
        freshness=freshness,
        confidence=ConfidenceLevel.MEDIUM,
        created_at=now,
        updated_at=now,
        last_checked=now,
        review_after=review_after,
        sources=sources or [],
        why_interesting="test",
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


def test_lint_clean_wiki_has_no_errors(vault: VaultPaths, conn) -> None:
    _write_page(
        vault,
        page_type=PageType.TOPIC,
        slug="alhambra",
        title="Alhambra",
        sources=["src_test"],
    )
    report = run_lint(conn, paths=vault)
    assert report.errors == 0


def test_lint_finds_page_without_sources(vault: VaultPaths, conn) -> None:
    _write_page(vault, page_type=PageType.TOPIC, slug="ohne-quellen", title="Ohne Quellen")
    report = run_lint(conn, paths=vault)
    assert any(f.finding_type == "page_without_sources" for f in report.findings)


def test_lint_finds_product_without_review_after(vault: VaultPaths, conn) -> None:
    _write_page(
        vault,
        page_type=PageType.PRODUCT_RESEARCH,
        slug="powerbank",
        title="Powerbank-Research",
        sources=["src_test"],
        freshness=Freshness.VOLATILE,
    )
    report = run_lint(conn, paths=vault)
    assert any(f.finding_type == "product_without_review_after" for f in report.findings)
    assert report.errors >= 1


def test_lint_finds_review_after_overdue(vault: VaultPaths, conn) -> None:
    target = _write_page(
        vault,
        page_type=PageType.PRODUCT_RESEARCH,
        slug="overdue",
        title="Overdue Page",
        sources=["src_test"],
        freshness=Freshness.VOLATILE,
    )
    text = target.read_text(encoding="utf-8")
    yesterday = (date.today() - timedelta(days=10)).isoformat()
    text = text.replace("review_after: null", f"review_after: {yesterday}")
    target.write_text(text, encoding="utf-8")
    report = run_lint(conn, paths=vault)
    assert any(f.finding_type == "review_after_overdue" for f in report.findings)


def test_lint_finds_hard_fact_without_claim(vault: VaultPaths, conn) -> None:
    _write_page(
        vault,
        page_type=PageType.TOPIC,
        slug="alhambra",
        title="Alhambra",
        sources=["src_test"],
        body_extra="\n\nDie Stätte wurde 1984 in die Welterbeliste aufgenommen.\n",
    )
    report = run_lint(conn, paths=vault)
    assert any(f.finding_type == "claim_missing_source" for f in report.findings)


def test_lint_skips_hard_fact_with_claim_marker(vault: VaultPaths, conn) -> None:
    body = (
        "\n\n## Belegte Fakten\n\n"
        "- Die Aufnahme erfolgte 1984.\n"
        "  - `claim:clm_x source:src_test type:year`\n"
    )
    _write_page(
        vault,
        page_type=PageType.TOPIC,
        slug="alhambra",
        title="Alhambra",
        sources=["src_test"],
        body_extra=body,
    )
    report = run_lint(conn, paths=vault)
    assert not any(f.finding_type == "claim_missing_source" for f in report.findings)


def test_lint_finds_broken_wikilink(vault: VaultPaths, conn) -> None:
    _write_page(
        vault,
        page_type=PageType.TOPIC,
        slug="alhambra",
        title="Alhambra",
        sources=["src_test"],
        body_extra="\n\nVerknuepft mit [[Nicht-existente Page]].\n",
    )
    report = run_lint(conn, paths=vault)
    assert any(f.finding_type == "broken_wikilink" for f in report.findings)


def test_lint_finds_duplicate_titles(vault: VaultPaths, conn) -> None:
    _write_page(vault, page_type=PageType.TOPIC, slug="alpha", title="Doppelt", sources=["src_a"])
    _write_page(vault, page_type=PageType.PLACE, slug="beta", title="Doppelt", sources=["src_b"])
    report = run_lint(conn, paths=vault)
    duplicates = [f for f in report.findings if f.finding_type == "duplicate_title"]
    assert len(duplicates) >= 2


def test_lint_persists_findings_to_registry(vault: VaultPaths, conn) -> None:
    _write_page(vault, page_type=PageType.TOPIC, slug="alhambra", title="Alhambra")
    report = run_lint(conn, paths=vault)
    rows = conn.execute(
        "SELECT findings_count FROM lint_runs WHERE id = ?", (report.run_id,)
    ).fetchone()
    assert rows is not None
    assert rows["findings_count"] == len(report.findings)


def test_lint_hard_fact_ignores_year_inside_wikilink(vault: VaultPaths, conn) -> None:
    """[[Pacojet 1984]] darf nicht als Year-Fakt zaehlen (Bugfix M4)."""
    _write_page(
        vault,
        page_type=PageType.METHOD,
        slug="pacojet",
        title="Pacojet",
        sources=["src_test"],
        body_extra="\n\nDer [[Pacojet 1984]] gilt als Vorlaeufer.\n",
    )
    report = run_lint(conn, paths=vault)
    assert not any(
        f.finding_type == "claim_missing_source" and "year" in f.message for f in report.findings
    )


def test_lint_orphan_page_when_no_backlinks(vault: VaultPaths, conn) -> None:
    """Page in DB ohne eingehende Wikilinks -> orphan_page-Finding (M4)."""
    from datetime import UTC, datetime

    from curiosity_wiki.wiki.repository import PageRepository

    now = datetime.now(tz=UTC)
    page = Page(
        id="page_TESTORPHAN",
        title="Orphan",
        slug="orphan",
        page_type=PageType.TOPIC,
        status=PageStatus.ACTIVE,
        freshness=Freshness.STABLE,
        confidence=ConfidenceLevel.MEDIUM,
        created_at=now,
        updated_at=now,
        sources=[],
        why_interesting="orphan test",
        llm_generated=False,
        human_reviewed=True,
        reviewed_at=now,
    )
    PageRepository(conn).insert(page)
    report = run_lint(conn, paths=vault)
    assert any(
        f.finding_type == "orphan_page" and f.page_id == "page_TESTORPHAN" for f in report.findings
    )


def test_lint_orphan_page_skips_source_and_question_types(vault: VaultPaths, conn) -> None:
    """Source-, Question-, Collection-Pages werden vom orphan-Check ausgenommen."""
    from datetime import UTC, datetime

    from curiosity_wiki.wiki.repository import PageRepository

    now = datetime.now(tz=UTC)
    repo = PageRepository(conn)
    for ptype, ident in [
        (PageType.SOURCE, "page_TESTSRC"),
        (PageType.QUESTION, "page_TESTQUESTION"),
        (PageType.COLLECTION, "page_TESTCOLL"),
    ]:
        repo.insert(
            Page(
                id=ident,
                title=f"{ptype.value}-page",
                slug=f"slug-{ptype.value}",
                page_type=ptype,
                status=PageStatus.ACTIVE,
                freshness=Freshness.STABLE,
                confidence=ConfidenceLevel.MEDIUM,
                created_at=now,
                updated_at=now,
                sources=[],
                why_interesting="exempt test",
                llm_generated=False,
                human_reviewed=True,
                reviewed_at=now,
            )
        )
    report = run_lint(conn, paths=vault)
    orphan_ids = {f.page_id for f in report.findings if f.finding_type == "orphan_page"}
    assert "page_TESTSRC" not in orphan_ids
    assert "page_TESTQUESTION" not in orphan_ids
    assert "page_TESTCOLL" not in orphan_ids


def test_lint_alias_collision_detected(vault: VaultPaths, conn) -> None:
    """Page A hat alias 'Foo'; Page B hat title 'Foo' -> alias_collision (M4)."""
    page_a = _write_page(
        vault, page_type=PageType.TOPIC, slug="alpha", title="Alpha", sources=["src_a"]
    )
    text = page_a.read_text(encoding="utf-8")
    text = text.replace("aliases: []", "aliases:\n- Foo")
    page_a.write_text(text, encoding="utf-8")
    _write_page(vault, page_type=PageType.PLACE, slug="foo-place", title="Foo", sources=["src_b"])
    report = run_lint(conn, paths=vault)
    assert any(f.finding_type == "alias_collision" for f in report.findings)
