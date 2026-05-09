"""SQLite-Repository für Extractions."""

from __future__ import annotations

import sqlite3
from datetime import datetime


class ExtractionRepository:
    """Schmales Persistenz-Layer um die ``extractions``-Tabelle."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def insert(
        self,
        *,
        extraction_id: str,
        source_id: str,
        extractor: str,
        extractor_version: str,
        input_sha256: str,
        output_path: str | None,
        output_sha256: str | None,
        output_chars: int | None,
        status: str,
        started_at: datetime,
        finished_at: datetime | None,
        warnings_json: str | None,
        error_message: str | None,
    ) -> None:
        self.conn.execute(
            """
            INSERT INTO extractions (
                id, source_id, extractor, extractor_version,
                input_sha256, output_path, output_sha256, output_chars,
                status, started_at, finished_at, warnings_json, error_message
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                extraction_id,
                source_id,
                extractor,
                extractor_version,
                input_sha256,
                output_path,
                output_sha256,
                output_chars,
                status,
                started_at.isoformat(timespec="seconds"),
                finished_at.isoformat(timespec="seconds") if finished_at else None,
                warnings_json,
                error_message,
            ),
        )

    def latest_for_source(self, source_id: str) -> sqlite3.Row | None:
        return self.conn.execute(
            "SELECT * FROM extractions WHERE source_id = ? ORDER BY started_at DESC LIMIT 1",
            (source_id,),
        ).fetchone()

    def update_source_status(self, source_id: str, status: str) -> None:
        from datetime import UTC

        self.conn.execute(
            "UPDATE sources SET status = ?, updated_at = ? WHERE id = ?",
            (status, datetime.now(tz=UTC).isoformat(timespec="seconds"), source_id),
        )
