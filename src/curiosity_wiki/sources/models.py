"""Domain-Modelle für Sources.

Reine Daten — keine I/O, keine SQL, keine HTTP. Diese Klassen sind
deserialisierbar nach SQLite-Rows und nach YAML-Frontmatter.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import StrEnum


class SourceType(StrEnum):
    """Quelltyp. Bestimmt Capture-Adapter und Standard-Pfad in ``raw/``."""

    WEB = "web"
    PDF = "pdf"
    FILE = "file"
    NOTE = "note"
    DATA = "data"
    SCREENSHOT = "screenshot"


class AccessType(StrEnum):
    """Zugänglichkeitsklasse — bestimmt Speicher- und Veröffentlichungs-Regeln."""

    PUBLIC = "public"
    PRIVATE = "private"
    PAYWALLED = "paywalled"
    OWN_NOTE = "own_note"


class CopyrightRisk(StrEnum):
    """Urheberrechts-Risiko."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Reliability(StrEnum):
    """Verlässlichkeit der Quelle."""

    OFFICIAL = "official"
    EXPERT = "expert"
    JOURNALISTIC = "journalistic"
    COMMERCIAL = "commercial"
    PERSONAL = "personal"
    UNKNOWN = "unknown"


class SourceStatus(StrEnum):
    """Verarbeitungs-Status der Quelle."""

    CAPTURED = "captured"
    EXTRACTED = "extracted"
    CLASSIFIED = "classified"
    PROPOSAL_CREATED = "proposal_created"
    INDEXED = "indexed"
    FAILED = "failed"
    QUARANTINED = "quarantined"


@dataclass
class Source:
    """Vollständige Source-Repräsentation."""

    id: str
    title: str | None
    source_type: SourceType
    original_url: str | None
    canonical_url: str | None
    captured_at: datetime
    raw_path: str
    extracted_path: str | None
    sha256: str
    bytes: int | None
    content_type: str | None
    language: str | None
    access: AccessType
    copyright_risk: CopyrightRisk
    reliability: Reliability
    llm_allowed: bool
    status: SourceStatus
    why_interesting: str
    license_note: str | None
    created_at: datetime
    updated_at: datetime

    def to_manifest_dict(self) -> dict[str, object]:
        """Repräsentation für YAML-Manifest (siehe ARD §7).

        Datetime-Werte werden zu ISO-Strings, Enums zu ihren Werten.
        """
        data = asdict(self)
        for key in ("captured_at", "created_at", "updated_at"):
            value = data[key]
            if isinstance(value, datetime):
                data[key] = value.isoformat(timespec="seconds")
        for key in ("source_type", "access", "copyright_risk", "reliability", "status"):
            value = data[key]
            if hasattr(value, "value"):
                data[key] = value.value
        return data


@dataclass
class SourceSnapshot:
    """Eine spezifische Version einer Source-Datei."""

    id: str
    source_id: str
    path: str
    sha256: str
    bytes: int | None
    content_type: str | None
    captured_at: datetime


@dataclass
class Job:
    """Hintergrund-Verarbeitungsaufgabe."""

    id: str
    job_type: str
    target_id: str | None
    status: str
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    error_message: str | None = None
    retry_count: int = 0


@dataclass(frozen=True)
class SourcePolicy:
    """Heuristische Quellen-Klassifizierung (Standard-Defaults)."""

    access: AccessType = AccessType.PUBLIC
    copyright_risk: CopyrightRisk = CopyrightRisk.LOW
    reliability: Reliability = Reliability.UNKNOWN
    llm_allowed: bool = True
    license_note: str | None = None
    notes: list[str] = field(default_factory=list)
