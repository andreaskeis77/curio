"""Quarantäne-Cases (siehe NEW NFL Lesson §4.5)."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class QuarantineCase:
    """Modellierung eines „etwas stimmt nicht"-Falls."""

    id: str
    case_type: str
    severity: str
    status: str
    created_at: datetime
    source_id: str | None = None
    run_id: str | None = None
    proposal_id: str | None = None
    owner: str | None = None
    resolved_at: datetime | None = None
    evidence: dict[str, Any] = field(default_factory=dict)
    recommended_action: str | None = None
    notes: str | None = None


class QuarantineRepository:
    """SQLite-Persistenz für ``quarantine_cases``."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def insert(self, case: QuarantineCase) -> None:
        self.conn.execute(
            """
            INSERT INTO quarantine_cases (
                id, case_type, severity, source_id, run_id, proposal_id,
                status, owner, created_at, resolved_at,
                evidence_json, recommended_action, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                case.id,
                case.case_type,
                case.severity,
                case.source_id,
                case.run_id,
                case.proposal_id,
                case.status,
                case.owner,
                case.created_at.isoformat(timespec="seconds"),
                case.resolved_at.isoformat(timespec="seconds") if case.resolved_at else None,
                json.dumps(case.evidence) if case.evidence else None,
                case.recommended_action,
                case.notes,
            ),
        )

    def list_open(self) -> list[QuarantineCase]:
        rows = self.conn.execute(
            "SELECT * FROM quarantine_cases WHERE status = 'open' ORDER BY created_at DESC"
        ).fetchall()
        return [_row_to_case(r) for r in rows]

    def count_by_type(self) -> dict[str, int]:
        rows = self.conn.execute(
            "SELECT case_type, COUNT(*) AS n FROM quarantine_cases GROUP BY case_type"
        ).fetchall()
        return {row["case_type"]: int(row["n"]) for row in rows}


def _row_to_case(row: sqlite3.Row) -> QuarantineCase:
    evidence = {}
    if row["evidence_json"]:
        try:
            evidence = json.loads(row["evidence_json"])
        except json.JSONDecodeError:
            evidence = {}
    return QuarantineCase(
        id=str(row["id"]),
        case_type=str(row["case_type"]),
        severity=str(row["severity"]),
        status=str(row["status"]),
        source_id=row["source_id"],
        run_id=row["run_id"],
        proposal_id=row["proposal_id"],
        owner=row["owner"],
        created_at=datetime.fromisoformat(row["created_at"]),
        resolved_at=datetime.fromisoformat(row["resolved_at"]) if row["resolved_at"] else None,
        evidence=evidence,
        recommended_action=row["recommended_action"],
        notes=row["notes"],
    )
