"""Sources-API."""

from __future__ import annotations

import sqlite3
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from curiosity_wiki.sources import SourceRepository, SourceStatus
from curiosity_wiki.web.dependencies import get_conn

router = APIRouter(tags=["sources"])


def _source_to_dict(source) -> dict[str, Any]:
    return {
        "id": source.id,
        "title": source.title,
        "type": source.source_type.value,
        "original_url": source.original_url,
        "access": source.access.value,
        "copyright_risk": source.copyright_risk.value,
        "reliability": source.reliability.value,
        "status": source.status.value,
        "captured_at": source.captured_at.isoformat(timespec="seconds"),
        "why_interesting": source.why_interesting,
    }


@router.get("/sources")
def list_sources(
    status: str | None = Query(None, description="Filter status"),
    limit: int = Query(50, ge=1, le=500),
    conn: sqlite3.Connection = Depends(get_conn),
) -> dict[str, Any]:
    repo = SourceRepository(conn)
    if status:
        try:
            items = repo.list_by_status(SourceStatus(status), limit=limit)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=f"unknown status: {status}") from exc
    else:
        items = repo.list_all(limit=limit)
    return {"count": len(items), "items": [_source_to_dict(s) for s in items]}


@router.get("/sources/{source_id}")
def source_detail(
    source_id: str,
    conn: sqlite3.Connection = Depends(get_conn),
) -> dict[str, Any]:
    source = SourceRepository(conn).get(source_id)
    if source is None:
        raise HTTPException(status_code=404, detail=f"source not found: {source_id}")
    payload = _source_to_dict(source)
    payload["raw_path"] = source.raw_path
    payload["sha256"] = source.sha256
    payload["language"] = source.language
    return payload
