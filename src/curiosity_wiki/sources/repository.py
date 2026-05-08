"""SQLite-Repository für Sources.

Zwei Aufgaben:

1. ``insert`` / ``get`` / ``list`` / ``find_by_url`` / ``find_by_hash``.
2. Duplicate Detection: gleiche URL oder gleicher SHA-256.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterable
from datetime import datetime

from curiosity_wiki.sources.models import (
    AccessType,
    CopyrightRisk,
    Reliability,
    Source,
    SourceStatus,
    SourceType,
)


class SourceRepository:
    """Dünnes Persistenz-Layer um die ``sources``-Tabelle."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def insert(self, source: Source) -> None:
        """Schreibt eine Source. Duplicate-Checks übernimmt der Aufrufer."""
        self.conn.execute(
            """
            INSERT INTO sources (
                id, title, source_type, original_url, canonical_url,
                captured_at, raw_path, extracted_path,
                sha256, bytes, content_type, language,
                access, copyright_risk, reliability, llm_allowed,
                status, why_interesting, license_note,
                created_at, updated_at
            ) VALUES (
                ?, ?, ?, ?, ?,
                ?, ?, ?,
                ?, ?, ?, ?,
                ?, ?, ?, ?,
                ?, ?, ?,
                ?, ?
            )
            """,
            (
                source.id,
                source.title,
                source.source_type.value,
                source.original_url,
                source.canonical_url,
                source.captured_at.isoformat(timespec="seconds"),
                source.raw_path,
                source.extracted_path,
                source.sha256,
                source.bytes,
                source.content_type,
                source.language,
                source.access.value,
                source.copyright_risk.value,
                source.reliability.value,
                1 if source.llm_allowed else 0,
                source.status.value,
                source.why_interesting,
                source.license_note,
                source.created_at.isoformat(timespec="seconds"),
                source.updated_at.isoformat(timespec="seconds"),
            ),
        )

    def get(self, source_id: str) -> Source | None:
        row = self.conn.execute(
            "SELECT * FROM sources WHERE id = ?",
            (source_id,),
        ).fetchone()
        return _row_to_source(row) if row is not None else None

    def find_by_url(self, url: str) -> Source | None:
        row = self.conn.execute(
            "SELECT * FROM sources WHERE original_url = ? LIMIT 1",
            (url,),
        ).fetchone()
        return _row_to_source(row) if row is not None else None

    def find_by_hash(self, sha256: str) -> Source | None:
        row = self.conn.execute(
            "SELECT * FROM sources WHERE sha256 = ? LIMIT 1",
            (sha256,),
        ).fetchone()
        return _row_to_source(row) if row is not None else None

    def list_all(self, limit: int = 200) -> list[Source]:
        rows = self.conn.execute(
            "SELECT * FROM sources ORDER BY captured_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [_row_to_source(r) for r in rows]

    def list_by_status(self, status: SourceStatus, limit: int = 200) -> list[Source]:
        rows = self.conn.execute(
            "SELECT * FROM sources WHERE status = ? ORDER BY captured_at DESC LIMIT ?",
            (status.value, limit),
        ).fetchall()
        return [_row_to_source(r) for r in rows]

    def count(self) -> int:
        row = self.conn.execute("SELECT COUNT(*) AS n FROM sources").fetchone()
        return int(row["n"]) if row else 0


def _row_to_source(row: sqlite3.Row | Iterable[object]) -> Source:
    data = dict(row)
    return Source(
        id=str(data["id"]),
        title=data.get("title"),
        source_type=SourceType(data["source_type"]),
        original_url=data.get("original_url"),
        canonical_url=data.get("canonical_url"),
        captured_at=datetime.fromisoformat(data["captured_at"]),
        raw_path=str(data["raw_path"]),
        extracted_path=data.get("extracted_path"),
        sha256=str(data["sha256"]),
        bytes=data.get("bytes"),
        content_type=data.get("content_type"),
        language=data.get("language"),
        access=AccessType(data["access"]),
        copyright_risk=CopyrightRisk(data["copyright_risk"]),
        reliability=Reliability(data["reliability"]),
        llm_allowed=bool(data.get("llm_allowed", 1)),
        status=SourceStatus(data["status"]),
        why_interesting=str(data["why_interesting"]),
        license_note=data.get("license_note"),
        created_at=datetime.fromisoformat(data["created_at"]),
        updated_at=datetime.fromisoformat(data["updated_at"]),
    )
