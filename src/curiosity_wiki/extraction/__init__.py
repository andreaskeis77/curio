"""curiosity_wiki.extraction — Markdown-Output aus heterogenen Rohquellen.

Public API:

- ``extract_source(source_id, conn, paths)``  : Top-Level-Aufruf.
- ``ExtractionResult``                         : strukturiertes Ergebnis.
- ``ExtractionRepository``                     : Persistenz in ``extractions``.

Adapter-Wahl folgt ADR-0011 (Format → Library) und ist in
``adapters.py`` gekapselt.
"""

from __future__ import annotations

from curiosity_wiki.extraction.pipeline import (
    ExtractionError,
    ExtractionResult,
    extract_source,
)
from curiosity_wiki.extraction.repository import ExtractionRepository

__all__ = [
    "ExtractionError",
    "ExtractionRepository",
    "ExtractionResult",
    "extract_source",
]
