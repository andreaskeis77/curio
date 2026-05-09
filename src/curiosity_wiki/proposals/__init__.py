"""curiosity_wiki.proposals — Proposal-Store und Ingest-Pipeline.

Public API:

- ``ingest_source`` — Top-Level: Source → LLM → Proposal auf Platte + DB.
- ``ProposalRecord`` — Metadaten eines Proposals.
- ``ProposalRepository`` — SQLite-Persistenz.
- ``QuarantineRepository`` — Quarantäne-Fälle.
"""

from __future__ import annotations

from curiosity_wiki.proposals.ingest import (
    IngestError,
    IngestResult,
    QuarantineDetected,
    ingest_source,
)
from curiosity_wiki.proposals.quarantine import QuarantineCase, QuarantineRepository
from curiosity_wiki.proposals.repository import ProposalRecord, ProposalRepository

__all__ = [
    "IngestError",
    "IngestResult",
    "ProposalRecord",
    "ProposalRepository",
    "QuarantineCase",
    "QuarantineDetected",
    "QuarantineRepository",
    "ingest_source",
]
