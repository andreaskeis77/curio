"""SQLite-Repository für Proposals."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime


@dataclass
class ProposalRecord:
    """Metadaten-Repräsentation eines Proposals (Inhalt liegt im Filesystem)."""

    id: str
    proposal_type: str
    source_id: str | None
    run_id: str | None
    path: str
    status: str
    risk_level: str | None
    new_pages_count: int
    hard_facts_count: int
    open_questions_count: int
    confidence: str | None
    created_at: datetime
    reviewed_at: datetime | None = None
    review_decision: str | None = None


class ProposalRepository:
    """Schmales Persistenz-Layer um die ``proposals``-Tabelle."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def insert(self, record: ProposalRecord) -> None:
        self.conn.execute(
            """
            INSERT INTO proposals (
                id, proposal_type, source_id, run_id, path, status, risk_level,
                new_pages_count, hard_facts_count, open_questions_count,
                confidence, created_at, reviewed_at, review_decision
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record.id,
                record.proposal_type,
                record.source_id,
                record.run_id,
                record.path,
                record.status,
                record.risk_level,
                record.new_pages_count,
                record.hard_facts_count,
                record.open_questions_count,
                record.confidence,
                record.created_at.isoformat(timespec="seconds"),
                record.reviewed_at.isoformat(timespec="seconds") if record.reviewed_at else None,
                record.review_decision,
            ),
        )

    def get(self, proposal_id: str) -> ProposalRecord | None:
        row = self.conn.execute(
            "SELECT * FROM proposals WHERE id = ?",
            (proposal_id,),
        ).fetchone()
        return _row_to_record(row) if row is not None else None

    def list_by_status(self, status: str, limit: int = 200) -> list[ProposalRecord]:
        rows = self.conn.execute(
            "SELECT * FROM proposals WHERE status = ? ORDER BY created_at DESC LIMIT ?",
            (status, limit),
        ).fetchall()
        return [_row_to_record(r) for r in rows]

    def list_all(self, limit: int = 200) -> list[ProposalRecord]:
        rows = self.conn.execute(
            "SELECT * FROM proposals ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [_row_to_record(r) for r in rows]

    def count_by_status(self) -> dict[str, int]:
        rows = self.conn.execute(
            "SELECT status, COUNT(*) AS n FROM proposals GROUP BY status"
        ).fetchall()
        return {row["status"]: int(row["n"]) for row in rows}

    def update_status(self, proposal_id: str, status: str, decision: str | None = None) -> None:
        self.conn.execute(
            "UPDATE proposals SET status = ?, reviewed_at = ?, review_decision = ? WHERE id = ?",
            (
                status,
                datetime.now(tz=UTC).isoformat(timespec="seconds"),
                decision,
                proposal_id,
            ),
        )


def _row_to_record(row: sqlite3.Row) -> ProposalRecord:
    return ProposalRecord(
        id=str(row["id"]),
        proposal_type=str(row["proposal_type"]),
        source_id=row["source_id"],
        run_id=row["run_id"],
        path=str(row["path"]),
        status=str(row["status"]),
        risk_level=row["risk_level"],
        new_pages_count=int(row["new_pages_count"] or 0),
        hard_facts_count=int(row["hard_facts_count"] or 0),
        open_questions_count=int(row["open_questions_count"] or 0),
        confidence=row["confidence"],
        created_at=datetime.fromisoformat(row["created_at"]),
        reviewed_at=datetime.fromisoformat(row["reviewed_at"]) if row["reviewed_at"] else None,
        review_decision=row["review_decision"],
    )
