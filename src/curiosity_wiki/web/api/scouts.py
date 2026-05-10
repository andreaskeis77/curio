"""Scouts-API: Liste mit letztem Lauf-Status (M7, ADR-0019)."""

from __future__ import annotations

import sqlite3
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from curiosity_wiki.paths import VaultPaths
from curiosity_wiki.scouts import ScoutLoadError, discover_scouts, load_scout
from curiosity_wiki.web.dependencies import get_conn, get_paths

router = APIRouter(prefix="/scouts", tags=["scouts"])


def _last_run(conn: sqlite3.Connection, scout_id: str) -> dict[str, Any] | None:
    row = conn.execute(
        """
        SELECT id, started_at, finished_at, status, sources_seen,
               captured, skipped, proposals, quarantined, errors, log_path
        FROM scout_runs
        WHERE scout_id = ?
        ORDER BY started_at DESC
        LIMIT 1
        """,
        (scout_id,),
    ).fetchone()
    if row is None:
        return None
    return {
        "run_id": row["id"],
        "started_at": row["started_at"],
        "finished_at": row["finished_at"],
        "status": row["status"],
        "sources_seen": int(row["sources_seen"] or 0),
        "captured": int(row["captured"] or 0),
        "skipped": int(row["skipped"] or 0),
        "proposals": int(row["proposals"] or 0),
        "quarantined": int(row["quarantined"] or 0),
        "errors": int(row["errors"] or 0),
        "log_path": row["log_path"],
    }


@router.get("")
def list_scouts(
    paths: VaultPaths = Depends(get_paths),
    conn: sqlite3.Connection = Depends(get_conn),
) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    for scout_path in discover_scouts(paths=paths):
        try:
            scout = load_scout(scout_path.stem, paths=paths)
        except ScoutLoadError as exc:
            items.append(
                {
                    "id": scout_path.stem,
                    "error": f"{exc}",
                }
            )
            continue
        items.append(
            {
                "id": scout.id,
                "domain": scout.domain,
                "description": scout.description,
                "frequency_hours": scout.frequency_hours,
                "sources_count": len(scout.sources),
                "last_run": _last_run(conn, scout.id),
            }
        )
    return {"count": len(items), "items": items}


@router.get("/{scout_id}")
def scout_detail(
    scout_id: str,
    paths: VaultPaths = Depends(get_paths),
    conn: sqlite3.Connection = Depends(get_conn),
) -> dict[str, Any]:
    try:
        scout = load_scout(scout_id, paths=paths)
    except ScoutLoadError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    runs = conn.execute(
        "SELECT id, started_at, finished_at, status, proposals, quarantined, errors "
        "FROM scout_runs WHERE scout_id = ? ORDER BY started_at DESC LIMIT 20",
        (scout_id,),
    ).fetchall()
    return {
        "id": scout.id,
        "domain": scout.domain,
        "description": scout.description,
        "prompt_id": scout.prompt_id,
        "frequency_hours": scout.frequency_hours,
        "sources": [
            {"type": s.type.value, "value": s.value, "title": s.title} for s in scout.sources
        ],
        "limits": {
            "max_sources_per_run": scout.limits.max_sources_per_run,
            "llm_allowed": scout.limits.llm_allowed,
            "dry_run": scout.limits.dry_run,
        },
        "recent_runs": [
            {
                "run_id": row["id"],
                "started_at": row["started_at"],
                "finished_at": row["finished_at"],
                "status": row["status"],
                "proposals": int(row["proposals"] or 0),
                "quarantined": int(row["quarantined"] or 0),
                "errors": int(row["errors"] or 0),
            }
            for row in runs
        ],
    }
