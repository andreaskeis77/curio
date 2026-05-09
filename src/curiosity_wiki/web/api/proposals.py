"""Proposals-API (read-only)."""

from __future__ import annotations

import sqlite3
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from curiosity_wiki.proposals import ProposalRepository
from curiosity_wiki.web.dependencies import get_conn

router = APIRouter(tags=["proposals"])


def _record_to_dict(record) -> dict[str, Any]:
    return {
        "id": record.id,
        "type": record.proposal_type,
        "source_id": record.source_id,
        "run_id": record.run_id,
        "status": record.status,
        "risk_level": record.risk_level,
        "new_pages_count": record.new_pages_count,
        "hard_facts_count": record.hard_facts_count,
        "open_questions_count": record.open_questions_count,
        "confidence": record.confidence,
        "created_at": record.created_at.isoformat(timespec="seconds"),
        "path": record.path,
    }


@router.get("/proposals")
def list_proposals(
    status: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    conn: sqlite3.Connection = Depends(get_conn),
) -> dict[str, Any]:
    repo = ProposalRepository(conn)
    items = repo.list_by_status(status, limit=limit) if status else repo.list_all(limit=limit)
    return {"count": len(items), "items": [_record_to_dict(r) for r in items]}


@router.get("/proposals/{proposal_id}")
def proposal_detail(
    proposal_id: str,
    conn: sqlite3.Connection = Depends(get_conn),
) -> dict[str, Any]:
    record = ProposalRepository(conn).get(proposal_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"proposal not found: {proposal_id}")
    return _record_to_dict(record)
