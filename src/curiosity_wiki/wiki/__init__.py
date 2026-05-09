"""curiosity_wiki.wiki — Page-Domain, Frontmatter, Repositories, Publish-Pipeline.

Public API:

- ``Page``, ``PageType``, ``PageStatus``, ``Freshness``, ``ConfidenceLevel``
- ``slugify`` — deterministischer Slug-Erzeuger (mit deutschen Umlauten).
- ``PageFrontmatter`` und ``validate_frontmatter``.
- ``PageRepository``, ``ClaimRepository``, ``LinkRepository``.
- ``publish_proposal`` — Top-Level-Publish.
"""

from __future__ import annotations

from curiosity_wiki.wiki.frontmatter import (
    FrontmatterError,
    PageFrontmatter,
    parse_frontmatter,
    render_frontmatter,
    validate_frontmatter,
)
from curiosity_wiki.wiki.models import (
    Claim,
    ConfidenceLevel,
    Freshness,
    Page,
    PageStatus,
    PageType,
    SourceRelation,
)
from curiosity_wiki.wiki.publish import (
    PublishError,
    PublishResult,
    SlugCollisionError,
    publish_proposal,
    reject_proposal,
    request_changes,
)
from curiosity_wiki.wiki.repository import (
    ClaimRepository,
    LinkRepository,
    PageRepository,
    PageSourceRepository,
)
from curiosity_wiki.wiki.slugify import slugify

__all__ = [
    "Claim",
    "ClaimRepository",
    "ConfidenceLevel",
    "Freshness",
    "FrontmatterError",
    "LinkRepository",
    "Page",
    "PageFrontmatter",
    "PageRepository",
    "PageSourceRepository",
    "PageStatus",
    "PageType",
    "PublishError",
    "PublishResult",
    "SlugCollisionError",
    "SourceRelation",
    "parse_frontmatter",
    "publish_proposal",
    "reject_proposal",
    "render_frontmatter",
    "request_changes",
    "slugify",
    "validate_frontmatter",
]
