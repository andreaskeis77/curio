"""Search-API ueber FTS5."""

from __future__ import annotations

import sqlite3
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from curiosity_wiki.search import SearchError, search_pages
from curiosity_wiki.web.dependencies import get_conn

router = APIRouter(tags=["search"])


@router.get("/search")
def search(
    q: str = Query(..., description="FTS5-Query"),
    page_type: str | None = Query(None, alias="type"),
    freshness: str | None = Query(None),
    status: str | None = Query(None),
    tag: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    conn: sqlite3.Connection = Depends(get_conn),
) -> dict[str, Any]:
    try:
        hits = search_pages(
            conn,
            q,
            page_type=page_type,
            freshness=freshness,
            status=status,
            tag=tag,
            limit=limit,
        )
    except SearchError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "count": len(hits),
        "query": q,
        "items": [
            {
                "page_id": hit.page_id,
                "title": hit.title,
                "type": hit.page_type,
                "freshness": hit.freshness,
                "status": hit.status,
                "rank": hit.rank,
                "snippet": hit.snippet,
                "path": hit.relative_path,
            }
            for hit in hits
        ],
    }
