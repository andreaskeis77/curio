"""SQLite-Repositories fuer Pages, Page-Sources, Claims, Links."""

from __future__ import annotations

import sqlite3
from datetime import datetime
from typing import Any

from curiosity_wiki.wiki.models import (
    Claim,
    ConfidenceLevel,
    Freshness,
    Page,
    PageStatus,
    PageType,
    SourceRelation,
)


def _iso(dt: datetime | None) -> str | None:
    return dt.isoformat(timespec="seconds") if dt else None


def _from_iso(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value else None


class PageRepository:
    """SQLite-Persistenz fuer ``pages``."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def insert(self, page: Page) -> None:
        self.conn.execute(
            """
            INSERT INTO pages (
                id, title, slug, path, type, status, freshness,
                last_checked, review_after, confidence, schema_version,
                proposal_id, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                page.id,
                page.title,
                page.slug,
                page.relative_path,
                page.page_type.value,
                page.status.value,
                page.freshness.value,
                _iso(page.last_checked),
                _iso(page.review_after),
                page.confidence.value,
                page.schema_version,
                page.proposal_id,
                _iso(page.created_at),
                _iso(page.updated_at),
            ),
        )

    def get(self, page_id: str) -> Page | None:
        row = self.conn.execute("SELECT * FROM pages WHERE id = ?", (page_id,)).fetchone()
        return _row_to_page(row) if row is not None else None

    def find_by_slug(self, slug: str, page_type: PageType) -> Page | None:
        row = self.conn.execute(
            "SELECT * FROM pages WHERE slug = ? AND type = ? LIMIT 1",
            (slug, page_type.value),
        ).fetchone()
        return _row_to_page(row) if row is not None else None

    def list_all(self, limit: int = 200) -> list[Page]:
        rows = self.conn.execute(
            "SELECT * FROM pages ORDER BY updated_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [_row_to_page(r) for r in rows]

    def list_by_type(self, page_type: PageType, limit: int = 200) -> list[Page]:
        rows = self.conn.execute(
            "SELECT * FROM pages WHERE type = ? ORDER BY updated_at DESC LIMIT ?",
            (page_type.value, limit),
        ).fetchall()
        return [_row_to_page(r) for r in rows]

    def count(self) -> int:
        row = self.conn.execute("SELECT COUNT(*) AS n FROM pages").fetchone()
        return int(row["n"]) if row else 0

    def existing_slugs(self, page_type: PageType) -> set[str]:
        rows = self.conn.execute(
            "SELECT slug FROM pages WHERE type = ?",
            (page_type.value,),
        ).fetchall()
        return {row["slug"] for row in rows}


class PageSourceRepository:
    """``page_sources``-Brueckentabelle."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def link(self, page_id: str, source_id: str, relation: SourceRelation) -> None:
        self.conn.execute(
            "INSERT OR IGNORE INTO page_sources(page_id, source_id, relation) VALUES (?, ?, ?)",
            (page_id, source_id, relation.value),
        )

    def list_for_page(self, page_id: str) -> list[tuple[str, str]]:
        rows = self.conn.execute(
            "SELECT source_id, relation FROM page_sources WHERE page_id = ?",
            (page_id,),
        ).fetchall()
        return [(row["source_id"], row["relation"]) for row in rows]


class ClaimRepository:
    """``claims``-Tabelle."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def insert(self, claim: Claim) -> None:
        self.conn.execute(
            """
            INSERT INTO claims (
                id, page_id, claim_text, claim_type, source_id, source_locator,
                confidence, verified_at, proposal_id, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                claim.id,
                claim.page_id,
                claim.claim_text,
                claim.claim_type,
                claim.source_id,
                claim.source_locator,
                claim.confidence.value,
                _iso(claim.verified_at),
                claim.proposal_id,
                _iso(claim.created_at),
                _iso(claim.updated_at),
            ),
        )

    def list_for_page(self, page_id: str) -> list[Claim]:
        rows = self.conn.execute(
            "SELECT * FROM claims WHERE page_id = ? ORDER BY created_at",
            (page_id,),
        ).fetchall()
        return [_row_to_claim(r) for r in rows]

    def count(self) -> int:
        row = self.conn.execute("SELECT COUNT(*) AS n FROM claims").fetchone()
        return int(row["n"]) if row else 0


class LinkRepository:
    """``links``-Tabelle (Wikilinks und Backlinks)."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def insert(
        self,
        from_page_id: str,
        to_page_id: str | None,
        target_text: str,
        *,
        link_type: str = "wikilink",
        status: str = "resolved",
    ) -> None:
        self.conn.execute(
            """
            INSERT INTO links (
                from_page_id, to_page_id, target_text, link_type, status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                from_page_id,
                to_page_id,
                target_text,
                link_type,
                status,
                datetime.now().astimezone().isoformat(timespec="seconds"),
            ),
        )

    def delete_for_page(self, page_id: str) -> None:
        self.conn.execute("DELETE FROM links WHERE from_page_id = ?", (page_id,))

    def backlinks(self, page_id: str) -> list[str]:
        rows = self.conn.execute(
            "SELECT from_page_id FROM links WHERE to_page_id = ?",
            (page_id,),
        ).fetchall()
        return [row["from_page_id"] for row in rows]

    def broken_links(self) -> list[sqlite3.Row]:
        rows = self.conn.execute("SELECT * FROM links WHERE status = 'broken'").fetchall()
        return list(rows)


def _row_to_page(row: sqlite3.Row) -> Page:
    data: dict[str, Any] = dict(row)
    return Page(
        id=str(data["id"]),
        title=str(data["title"]),
        slug=str(data["slug"]),
        page_type=PageType(data["type"]),
        status=PageStatus(data["status"]),
        freshness=Freshness(data["freshness"]) if data["freshness"] else Freshness.STABLE,
        confidence=ConfidenceLevel(data["confidence"])
        if data["confidence"]
        else ConfidenceLevel.LOW,
        last_checked=_from_iso(data["last_checked"]),
        review_after=_from_iso(data["review_after"]),
        proposal_id=data["proposal_id"],
        schema_version=int(data["schema_version"] or 1),
        created_at=_from_iso(data["created_at"]) or datetime.now().astimezone(),
        updated_at=_from_iso(data["updated_at"]) or datetime.now().astimezone(),
    )


def _row_to_claim(row: sqlite3.Row) -> Claim:
    data = dict(row)
    return Claim(
        id=str(data["id"]),
        page_id=str(data["page_id"]),
        claim_text=str(data["claim_text"]),
        claim_type=str(data["claim_type"]),
        source_id=str(data["source_id"]),
        source_locator=data["source_locator"],
        confidence=ConfidenceLevel(data["confidence"]),
        verified_at=_from_iso(data["verified_at"]),
        proposal_id=data["proposal_id"],
        created_at=_from_iso(data["created_at"]) or datetime.now().astimezone(),
        updated_at=_from_iso(data["updated_at"]) or datetime.now().astimezone(),
    )
