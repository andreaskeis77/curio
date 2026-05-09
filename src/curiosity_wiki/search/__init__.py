"""curiosity_wiki.search — FTS5-Suche und Index-Pflege (M4, ADR-0014)."""

from __future__ import annotations

from curiosity_wiki.search.index import (
    RebuildResult,
    delete_page,
    index_page,
    rebuild_index_from_markdown,
)
from curiosity_wiki.search.search import SearchError, SearchHit, search_pages

__all__ = [
    "RebuildResult",
    "SearchError",
    "SearchHit",
    "delete_page",
    "index_page",
    "rebuild_index_from_markdown",
    "search_pages",
]
