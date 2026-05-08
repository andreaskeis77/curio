"""curiosity_wiki.sources — Source-Erfassung und -Verwaltung.

Public API:

- ``Source`` (dataclass)            : kanonische Source-Repräsentation.
- ``SourceType``, ``AccessType``,
  ``CopyrightRisk``, ``Reliability``,
  ``SourceStatus``                  : kontrollierte Vokabularen.
- ``capture_url`` / ``capture_file`` /
  ``capture_note``                  : Capture-Adapter.
- ``SourceRepository``              : SQLite-Persistenz.
- ``guess_source_policy``           : Domain-basierte Heuristik.
"""

from __future__ import annotations

from curiosity_wiki.sources.capture import (
    CaptureError,
    DuplicateSourceError,
    capture_file,
    capture_note,
    capture_url,
)
from curiosity_wiki.sources.models import (
    AccessType,
    CopyrightRisk,
    Reliability,
    Source,
    SourceStatus,
    SourceType,
)
from curiosity_wiki.sources.policy import guess_source_policy
from curiosity_wiki.sources.repository import SourceRepository

__all__ = [
    "AccessType",
    "CaptureError",
    "CopyrightRisk",
    "DuplicateSourceError",
    "Reliability",
    "Source",
    "SourceRepository",
    "SourceStatus",
    "SourceType",
    "capture_file",
    "capture_note",
    "capture_url",
    "guess_source_policy",
]
