"""Lint-API: zeigt den letzten Lint-Run + Findings."""

from __future__ import annotations

import sqlite3
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from curiosity_wiki.web.dependencies import get_conn

router = APIRouter(prefix="/lint", tags=["lint"])


@router.get("/report/latest")
def latest_lint_report(conn: sqlite3.Connection = Depends(get_conn)) -> dict[str, Any]:
    run_row = conn.execute("SELECT * FROM lint_runs ORDER BY started_at DESC LIMIT 1").fetchone()
    if run_row is None:
        raise HTTPException(status_code=404, detail="no lint run yet")
    findings = conn.execute(
        "SELECT severity, finding_type, page_id, source_id, file_path, message "
        "FROM lint_findings WHERE lint_run_id = ? ORDER BY severity, finding_type",
        (run_row["id"],),
    ).fetchall()
    return {
        "run_id": run_row["id"],
        "started_at": run_row["started_at"],
        "finished_at": run_row["finished_at"],
        "status": run_row["status"],
        "errors": run_row["errors_count"],
        "warnings": run_row["warnings_count"],
        "findings_count": run_row["findings_count"],
        "findings": [
            {
                "severity": row["severity"],
                "type": row["finding_type"],
                "page_id": row["page_id"],
                "source_id": row["source_id"],
                "file_path": row["file_path"],
                "message": row["message"],
            }
            for row in findings
        ],
    }
