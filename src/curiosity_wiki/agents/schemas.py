"""Pydantic-Schemata für Agent-Outputs.

Aktuell nur ``IngestProposalV1``. Weitere Schemata (Link, Lint, Query)
folgen mit den jeweiligen Tranchen.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class ConfidenceLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class FreshnessProfile(StrEnum):
    STABLE = "stable"
    PERIODIC = "periodic"
    VOLATILE = "volatile"
    PERSONAL = "personal"


class PageType(StrEnum):
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


class RiskSeverity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class RiskType(StrEnum):
    HALLUCINATION_RISK = "hallucination_risk"
    PROMPT_INJECTION = "prompt_injection"
    SOURCE_POLICY = "source_policy"
    UNVERIFIED_CLAIM = "unverified_claim"
    DUPLICATE_RISK = "duplicate_risk"
    SCHEMA_DRIFT = "schema_drift"


class ProposedSection(BaseModel):
    model_config = ConfigDict(extra="forbid")
    heading: str
    markdown: str


class ProposedPage(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str
    slug: str | None = None
    type: PageType
    sources: list[str] = Field(default_factory=list)
    sections: list[ProposedSection] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    why_interesting: str | None = None
    confidence: ConfidenceLevel = ConfidenceLevel.LOW


class HardFact(BaseModel):
    model_config = ConfigDict(extra="forbid")
    claim_text: str
    claim_type: str
    source_id: str
    confidence: ConfidenceLevel = ConfidenceLevel.LOW


class RiskNote(BaseModel):
    model_config = ConfigDict(extra="forbid")
    risk_type: RiskType
    severity: RiskSeverity
    description: str


class FreshnessRecommendation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    page_title: str
    freshness: FreshnessProfile
    review_after_days: int | None = None


class IngestProposalV1(BaseModel):
    """Output-Schema für ``ingest_v0_1``."""

    model_config = ConfigDict(extra="forbid")

    new_pages: list[ProposedPage] = Field(default_factory=list)
    hard_facts: list[HardFact] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    risk_notes: list[RiskNote] = Field(default_factory=list)
    freshness_recommendations: list[FreshnessRecommendation] = Field(default_factory=list)
    overall_confidence: ConfidenceLevel = ConfidenceLevel.LOW
    summary: str = ""
