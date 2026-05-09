"""Tests fuer Page-Frontmatter Render/Parse/Validate."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from curiosity_wiki.wiki.frontmatter import (
    FrontmatterError,
    parse_frontmatter,
    render_frontmatter,
    validate_frontmatter,
)
from curiosity_wiki.wiki.models import (
    ConfidenceLevel,
    Freshness,
    Page,
    PageStatus,
    PageType,
)


def _sample_page() -> Page:
    now = datetime(2026, 5, 9, 12, 0, 0, tzinfo=UTC)
    return Page(
        id="page_01HX9W2M6YK7K8E6J4N2Z7T1QK",
        title="Test Page",
        slug="test-page",
        page_type=PageType.TOPIC,
        status=PageStatus.ACTIVE,
        freshness=Freshness.STABLE,
        confidence=ConfidenceLevel.MEDIUM,
        created_at=now,
        updated_at=now,
        sources=["src_test"],
        tags=["pilot"],
        why_interesting="Beispiel-Page",
        llm_generated=True,
        human_reviewed=True,
        reviewed_at=now,
    )


def test_render_and_parse_roundtrip() -> None:
    page = _sample_page()
    rendered = render_frontmatter(page)
    front, body = parse_frontmatter(rendered + "\n# Body\n\nHello")
    assert front.data["id"] == page.id
    assert front.data["slug"] == page.slug
    assert front.data["type"] == "topic"
    assert "# Body" in body


def test_validate_accepts_valid_page() -> None:
    page = _sample_page()
    rendered = render_frontmatter(page)
    front, _ = parse_frontmatter(rendered + "body")
    errors = validate_frontmatter(front)
    assert errors == []


def test_validate_rejects_missing_keys() -> None:
    text = "---\nid: page_x\ntitle: t\n---\n\nbody"
    front, _ = parse_frontmatter(text)
    errors = validate_frontmatter(front)
    assert any("missing required keys" in e for e in errors)


def test_validate_rejects_bad_enum() -> None:
    page = _sample_page()
    rendered = render_frontmatter(page).replace("type: topic", "type: not-a-type")
    front, _ = parse_frontmatter(rendered + "body")
    errors = validate_frontmatter(front)
    assert any("invalid type" in e for e in errors)


def test_validate_rejects_bad_id_prefix() -> None:
    page = _sample_page()
    rendered = render_frontmatter(page).replace("id: page_01HX9W2M6YK7K8E6J4N2Z7T1QK", "id: foo_x")
    front, _ = parse_frontmatter(rendered + "body")
    errors = validate_frontmatter(front)
    assert any("id must start" in e for e in errors)


def test_parse_without_frontmatter_raises() -> None:
    with pytest.raises(FrontmatterError):
        parse_frontmatter("# No frontmatter\n\nbody")
