"""curiosity_wiki.browse — Lesepfade ueber Wiki-Pages (M4)."""

from __future__ import annotations

from curiosity_wiki.browse.explorer import (
    BrowseEntry,
    browse_by_collection,
    browse_by_topic,
    browse_random,
)

__all__ = [
    "BrowseEntry",
    "browse_by_collection",
    "browse_by_topic",
    "browse_random",
]
