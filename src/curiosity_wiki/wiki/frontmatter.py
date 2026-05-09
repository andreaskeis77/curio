"""YAML-Frontmatter fuer Wiki-Pages: Render, Parse, Validate.

Schema (siehe ARD §7) — Pflichtfelder:

- ``id``, ``title``, ``slug``, ``type``, ``status``, ``created``, ``updated``,
  ``freshness``, ``confidence``, ``schema_version``, ``llm_generated``,
  ``human_reviewed``.

Optional: ``last_checked``, ``review_after``, ``sources``, ``tags``,
``aliases``, ``why_interesting``, ``reviewed_at``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

import yaml

from curiosity_wiki.wiki.models import (
    ConfidenceLevel,
    Freshness,
    Page,
    PageStatus,
    PageType,
)

FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", re.DOTALL)


class FrontmatterError(ValueError):
    """Fehlt etwas Pflichtmaessiges oder ist es ungueltig."""


@dataclass(frozen=True)
class PageFrontmatter:
    """Strukturierte Frontmatter-Repraesentation."""

    data: dict[str, Any]

    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)


REQUIRED_KEYS = {
    "id",
    "title",
    "slug",
    "type",
    "status",
    "created",
    "updated",
    "freshness",
    "confidence",
    "schema_version",
    "llm_generated",
    "human_reviewed",
}


def _coerce_iso(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, datetime):
        return value.isoformat(timespec="seconds")
    if isinstance(value, date):
        return value.isoformat()
    return str(value)


def render_frontmatter(page: Page) -> str:
    """YAML-Block (mit ``---`` Markern) fuer Page-Frontmatter."""
    front: dict[str, Any] = {
        "id": page.id,
        "title": page.title,
        "slug": page.slug,
        "type": page.page_type.value,
        "status": page.status.value,
        "created": _coerce_iso(page.created_at),
        "updated": _coerce_iso(page.updated_at),
        "freshness": page.freshness.value,
        "last_checked": _coerce_iso(page.last_checked) if page.last_checked else None,
        "review_after": _coerce_iso(page.review_after) if page.review_after else None,
        "confidence": page.confidence.value,
        "sources": list(page.sources),
        "tags": list(page.tags),
        "aliases": list(page.aliases),
        "why_interesting": page.why_interesting,
        "llm_generated": page.llm_generated,
        "human_reviewed": page.human_reviewed,
        "reviewed_at": _coerce_iso(page.reviewed_at) if page.reviewed_at else None,
        "schema_version": page.schema_version,
        "proposal_id": page.proposal_id,
    }
    body = yaml.safe_dump(front, allow_unicode=True, sort_keys=False).strip()
    return f"---\n{body}\n---\n"


def parse_frontmatter(text: str) -> tuple[PageFrontmatter, str]:
    """Liefert ``(frontmatter, body)``.

    Wirft ``FrontmatterError``, wenn der Text keinen Frontmatter-Block hat.
    """
    match = FRONTMATTER_RE.match(text)
    if not match:
        raise FrontmatterError("text does not start with a YAML frontmatter block")
    front_text = match.group(1)
    body = match.group(2)
    try:
        data = yaml.safe_load(front_text) or {}
    except yaml.YAMLError as exc:
        raise FrontmatterError(f"invalid YAML in frontmatter: {exc}") from exc
    if not isinstance(data, dict):
        raise FrontmatterError("frontmatter must be a mapping")
    return PageFrontmatter(data=data), body


def validate_frontmatter(front: PageFrontmatter) -> list[str]:
    """Prueft Pflichtfelder und Enum-Werte. Liefert Liste von Fehlern."""
    errors: list[str] = []
    missing = REQUIRED_KEYS - set(front.data.keys())
    if missing:
        errors.append(f"missing required keys: {sorted(missing)}")
        return errors

    # Enum-Validierung
    try:
        PageType(str(front.data["type"]))
    except ValueError:
        errors.append(f"invalid type: {front.data['type']!r}")
    try:
        PageStatus(str(front.data["status"]))
    except ValueError:
        errors.append(f"invalid status: {front.data['status']!r}")
    try:
        Freshness(str(front.data["freshness"]))
    except ValueError:
        errors.append(f"invalid freshness: {front.data['freshness']!r}")
    try:
        ConfidenceLevel(str(front.data["confidence"]))
    except ValueError:
        errors.append(f"invalid confidence: {front.data['confidence']!r}")

    # ID-Praefix
    if not str(front.data["id"]).startswith("page_"):
        errors.append(f"id must start with 'page_': {front.data['id']!r}")

    # Slug
    slug = str(front.data["slug"])
    if not slug or " " in slug:
        errors.append(f"invalid slug: {slug!r}")

    # Booleans
    for key in ("llm_generated", "human_reviewed"):
        if not isinstance(front.data[key], bool):
            errors.append(f"{key} must be boolean, got {type(front.data[key]).__name__}")

    return errors
