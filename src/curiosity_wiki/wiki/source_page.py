"""Source-Page-Generator.

Pro veroeffentlichter Source wird eine Source-Page ``wiki/sources/<slug>.md``
erzeugt. Sie ist der Verweis-Anker fuer Wiki-Pages und enthaelt Metadaten
plus Link auf den Raw-Snapshot.
"""

from __future__ import annotations

from datetime import datetime

from curiosity_wiki.sources.models import Source
from curiosity_wiki.wiki.frontmatter import render_frontmatter
from curiosity_wiki.wiki.models import (
    ConfidenceLevel,
    Freshness,
    Page,
    PageStatus,
    PageType,
)
from curiosity_wiki.wiki.slugify import disambiguate, slugify


def build_source_page(
    source: Source,
    *,
    page_id: str,
    proposal_id: str | None,
    existing_slugs: set[str],
    now: datetime,
) -> tuple[Page, str]:
    """Liefert ``(Page, full_markdown)`` fuer eine Source-Page."""
    desired_slug = slugify(source.title or source.id)
    slug = disambiguate(desired_slug, existing_slugs)

    page = Page(
        id=page_id,
        title=source.title or source.id,
        slug=slug,
        page_type=PageType.SOURCE,
        status=PageStatus.ACTIVE,
        freshness=Freshness.STABLE,
        confidence=ConfidenceLevel.MEDIUM,
        created_at=now,
        updated_at=now,
        proposal_id=proposal_id,
        sources=[source.id],
        why_interesting=source.why_interesting,
        llm_generated=False,
        human_reviewed=True,
        reviewed_at=now,
    )
    body = _render_source_body(source)
    full = render_frontmatter(page) + "\n" + body
    return page, full


def _render_source_body(source: Source) -> str:
    lines = [
        f"# {source.title or source.id}",
        "",
        f"> {source.why_interesting}",
        "",
        "## Quellen-Metadaten",
        "",
        f"- **Source-ID:** `{source.id}`",
        f"- **Typ:** `{source.source_type.value}`",
        f"- **Erfasst:** {source.captured_at.isoformat(timespec='seconds')}",
        f"- **SHA-256:** `{source.sha256}`",
        f"- **Access:** `{source.access.value}`",
        f"- **Copyright Risk:** `{source.copyright_risk.value}`",
        f"- **Reliability:** `{source.reliability.value}`",
        f"- **LLM erlaubt:** `{source.llm_allowed}`",
    ]
    if source.original_url:
        lines.append(f"- **URL:** [{source.original_url}]({source.original_url})")
    if source.license_note:
        lines.append(f"- **Lizenz-Hinweis:** {source.license_note}")
    lines.extend(["", "## Raw-Snapshot", "", f"`{source.raw_path}`", ""])
    if source.extracted_path:
        lines.extend(["## Extracted", "", f"`{source.extracted_path}`", ""])
    lines.extend(["## Notizen", "", "_(zu ergaenzen)_", ""])
    return "\n".join(lines)
