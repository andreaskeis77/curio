"""Suche ueber ``pages_fts`` mit Filter-Joins auf ``pages`` (ADR-0014)."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from curiosity_wiki.wiki.models import Freshness, PageStatus, PageType


@dataclass
class SearchHit:
    """Ein Treffer aus der Volltextsuche."""

    page_id: str
    title: str
    page_type: str
    freshness: str
    status: str
    rank: float
    snippet: str
    relative_path: str


class SearchError(RuntimeError):
    """Suche fehlgeschlagen — etwa wegen FTS-MATCH-Syntaxfehler."""


_VALID_TYPES = {p.value for p in PageType}
_VALID_FRESHNESS = {f.value for f in Freshness}
_VALID_STATUS = {s.value for s in PageStatus}


def _validate(value: str | None, allowed: set[str], label: str) -> None:
    if value is not None and value not in allowed:
        raise SearchError(f"unknown {label}: {value!r}. Allowed: {', '.join(sorted(allowed))}")


def search_pages(
    conn: sqlite3.Connection,
    query: str,
    *,
    page_type: str | None = None,
    freshness: str | None = None,
    status: str | None = None,
    tag: str | None = None,
    limit: int = 20,
) -> list[SearchHit]:
    """FTS5-Suche mit optionalen Filtern.

    ``query`` wird als FTS5 MATCH-Expression interpretiert. Filter werden ueber
    Join auf ``pages`` und gegebenenfalls auf den ``tags``-Spalteninhalt der
    FTS-Zeile angewendet.
    """
    if not query or not query.strip():
        return []
    _validate(page_type, _VALID_TYPES, "page type")
    _validate(freshness, _VALID_FRESHNESS, "freshness")
    _validate(status, _VALID_STATUS, "status")

    conditions = ["pages_fts MATCH ?"]
    params: list[object] = [query]
    if page_type:
        conditions.append("p.type = ?")
        params.append(page_type)
    if freshness:
        conditions.append("p.freshness = ?")
        params.append(freshness)
    if status:
        conditions.append("p.status = ?")
        params.append(status)
    if tag:
        # Tags sind im FTS-Body als Whitespace-getrennte Liste.
        conditions.append("pages_fts.tags LIKE ?")
        params.append(f"%{tag}%")

    sql = f"""
        SELECT p.id          AS page_id,
               p.title       AS title,
               p.type        AS type,
               p.freshness   AS freshness,
               p.status      AS status,
               p.path        AS path,
               bm25(pages_fts) AS rank,
               snippet(pages_fts, 2, '<<', '>>', ' ... ', 12) AS snippet
        FROM pages_fts
        JOIN pages p ON p.id = pages_fts.page_id
        WHERE {" AND ".join(conditions)}
        ORDER BY rank
        LIMIT ?
    """
    params.append(int(limit))
    try:
        rows = conn.execute(sql, params).fetchall()
    except sqlite3.OperationalError as exc:
        raise SearchError(f"FTS query failed: {exc}") from exc
    return [
        SearchHit(
            page_id=row["page_id"],
            title=row["title"],
            page_type=row["type"],
            freshness=row["freshness"] or "",
            status=row["status"],
            rank=float(row["rank"]),
            snippet=row["snippet"] or "",
            relative_path=row["path"],
        )
        for row in rows
    ]
