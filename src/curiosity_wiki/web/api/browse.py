"""Browse-API: Random-Walk, Topic, Collection."""

from __future__ import annotations

import sqlite3
from typing import Any

from fastapi import APIRouter, Depends, Query

from curiosity_wiki.browse import (
    browse_by_collection,
    browse_by_topic,
    browse_random,
)
from curiosity_wiki.web.dependencies import get_conn

router = APIRouter(prefix="/browse", tags=["browse"])


def _entry_to_dict(entry) -> dict[str, Any]:
    return {
        "page_id": entry.page_id,
        "title": entry.title,
        "type": entry.page_type,
        "freshness": entry.freshness,
        "path": entry.relative_path,
    }


@router.get("/random-walk")
def random_walk(
    n: int = Query(5, ge=1, le=50),
    conn: sqlite3.Connection = Depends(get_conn),
) -> dict[str, Any]:
    entries = browse_random(conn, limit=n)
    return {"count": len(entries), "items": [_entry_to_dict(e) for e in entries]}


@router.get("/topic/{name}")
def topic(
    name: str,
    limit: int = Query(50, ge=1, le=200),
    conn: sqlite3.Connection = Depends(get_conn),
) -> dict[str, Any]:
    entries = browse_by_topic(conn, name, limit=limit)
    return {"topic": name, "count": len(entries), "items": [_entry_to_dict(e) for e in entries]}


@router.get("/collection/{name}")
def collection(
    name: str,
    limit: int = Query(50, ge=1, le=200),
    conn: sqlite3.Connection = Depends(get_conn),
) -> dict[str, Any]:
    entries = browse_by_collection(conn, name, limit=limit)
    return {
        "collection": name,
        "count": len(entries),
        "items": [_entry_to_dict(e) for e in entries],
    }
