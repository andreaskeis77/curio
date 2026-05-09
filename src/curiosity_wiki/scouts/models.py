"""Scout-Schema (Pydantic) — siehe ADR-0019."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ScoutSourceType(StrEnum):
    """Capture-Adapter, der pro Source-Eintrag genutzt wird."""

    URL = "url"
    NOTE = "note"
    FILE = "file"


class ScoutSource(BaseModel):
    """Eine Quelle innerhalb eines Scouts."""

    model_config = ConfigDict(extra="forbid")

    type: ScoutSourceType
    value: str = Field(min_length=1, description="URL, Note-Text oder Dateipfad.")
    why_interesting: str = Field(default="", description="Optionaler Kontext fuers Capture.")
    title: str | None = Field(default=None, description="Optionaler Titel.")


class ScoutLimits(BaseModel):
    """Operative Hard-Limits."""

    model_config = ConfigDict(extra="forbid")

    max_sources_per_run: int = Field(default=20, ge=1, le=200)
    llm_allowed: bool = True
    dry_run: bool = False


class ScoutQuarantineConfig(BaseModel):
    """Quarantaene-Verhalten (Reuse von M2)."""

    model_config = ConfigDict(extra="forbid")

    on_injection: bool = True
    on_schema_drift: bool = True


class ScoutDefinition(BaseModel):
    """Eine Scout-YAML, geladen und validiert."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, pattern=r"^[a-z0-9][a-z0-9-]*$")
    domain: str = Field(min_length=1)
    description: str = ""
    prompt_id: str = Field(min_length=1, default="ingest_v0_1")
    frequency_hours: float = Field(default=24.0, ge=0.0)
    sources: list[ScoutSource] = Field(min_length=1)
    limits: ScoutLimits = Field(default_factory=ScoutLimits)
    quarantine: ScoutQuarantineConfig = Field(default_factory=ScoutQuarantineConfig)

    @field_validator("sources")
    @classmethod
    def _validate_sources(cls, v: list[ScoutSource]) -> list[ScoutSource]:
        if not v:
            raise ValueError("at least one source required")
        return v
