"""Wiki-Domain-Modelle: Page, Claim, Enums.

Pure Daten — keine I/O, keine SQL, keine Markdown-Logik.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum


class PageType(StrEnum):
    """Wiki-Seitentypen (siehe ARD §7)."""

    SOURCE = "source"
    TOPIC = "topic"
    PERSON = "person"
    PLACE = "place"
    EVENT = "event"
    PRODUCT_RESEARCH = "product_research"
    RECIPE = "recipe"
    METHOD = "method"
    EXPERIMENT = "experiment"
    COLLECTION = "collection"
    QUESTION = "question"
    WORK = "work"
    BRAND = "brand"


class PageStatus(StrEnum):
    """Veroeffentlichungs-Status."""

    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"


class Freshness(StrEnum):
    """Aktualitaets-Profil."""

    STABLE = "stable"
    PERIODIC = "periodic"
    VOLATILE = "volatile"
    PERSONAL = "personal"


class ConfidenceLevel(StrEnum):
    """Vertrauensniveau."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class SourceRelation(StrEnum):
    """Page-zu-Source-Beziehung."""

    PRIMARY = "primary"
    SUPPORTING = "supporting"
    DERIVED = "derived"


# Zuordnung PageType -> wiki/<dir>/
TYPE_TO_DIR: dict[PageType, str] = {
    PageType.SOURCE: "sources",
    PageType.TOPIC: "topics",
    PageType.PERSON: "people",
    PageType.PLACE: "places",
    PageType.EVENT: "events",
    PageType.PRODUCT_RESEARCH: "products",
    PageType.RECIPE: "recipes",
    PageType.METHOD: "methods",
    PageType.EXPERIMENT: "experiments",
    PageType.COLLECTION: "collections",
    PageType.QUESTION: "questions",
    PageType.WORK: "works",
    PageType.BRAND: "brands",
}


@dataclass
class Page:
    """Wiki-Seite mit Frontmatter und Body-Inhalt."""

    id: str
    title: str
    slug: str
    page_type: PageType
    status: PageStatus
    freshness: Freshness
    confidence: ConfidenceLevel
    created_at: datetime
    updated_at: datetime
    last_checked: datetime | None = None
    review_after: datetime | None = None
    proposal_id: str | None = None
    schema_version: int = 1
    body_markdown: str = ""
    sources: list[str] = field(default_factory=list)  # Source-IDs
    tags: list[str] = field(default_factory=list)
    aliases: list[str] = field(default_factory=list)
    why_interesting: str = ""
    llm_generated: bool = False
    human_reviewed: bool = False
    reviewed_at: datetime | None = None

    @property
    def relative_path(self) -> str:
        """Pfad relativ zum Vault-Root: ``wiki/<dir>/<slug>.md``."""
        return f"wiki/{TYPE_TO_DIR[self.page_type]}/{self.slug}.md"


@dataclass
class Claim:
    """Harter Fakt mit Quellenbindung (ADR-0013)."""

    id: str
    page_id: str
    claim_text: str
    claim_type: str  # year | number | price | spec | quote | location | percent | other
    source_id: str
    confidence: ConfidenceLevel
    created_at: datetime
    updated_at: datetime
    source_locator: str | None = None
    verified_at: datetime | None = None
    proposal_id: str | None = None
