"""Lesepfade: random, by-topic, by-collection (M4)."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass


@dataclass
class BrowseEntry:
    """Ein Treffer im Lesepfad."""

    page_id: str
    title: str
    page_type: str
    relative_path: str
    freshness: str
    why_interesting: str = ""


def _row_to_entry(row: sqlite3.Row) -> BrowseEntry:
    return BrowseEntry(
        page_id=str(row["id"]),
        title=str(row["title"]),
        page_type=str(row["type"]),
        relative_path=str(row["path"]),
        freshness=str(row["freshness"] or ""),
    )


def browse_random(
    conn: sqlite3.Connection,
    *,
    limit: int = 5,
    exclude_types: set[str] | None = None,
) -> list[BrowseEntry]:
    """Liefert zufaellige Pages mit Status active.

    ``exclude_types`` blendet z.B. Source-Pages aus, die selten als Lesepfad sinnvoll sind.
    """
    exclude_types = exclude_types or {"source"}
    if exclude_types:
        placeholders = ",".join("?" for _ in exclude_types)
        sql = (
            f"SELECT id, title, type, path, freshness FROM pages "
            f"WHERE status = 'active' AND type NOT IN ({placeholders}) "
            f"ORDER BY RANDOM() LIMIT ?"
        )
        params: list[object] = [*exclude_types, int(limit)]
    else:
        sql = (
            "SELECT id, title, type, path, freshness FROM pages "
            "WHERE status = 'active' ORDER BY RANDOM() LIMIT ?"
        )
        params = [int(limit)]
    rows = conn.execute(sql, params).fetchall()
    return [_row_to_entry(row) for row in rows]


def browse_by_topic(
    conn: sqlite3.Connection,
    topic: str,
    *,
    limit: int = 50,
) -> list[BrowseEntry]:
    """Pages, die zur Topic-Page mit ``topic`` als Title verlinkt sind.

    Fallback: wenn keine Topic-Page existiert, sucht ``LIKE``-basiert auf
    Page-Titeln. So bleibt Browse benutzbar, auch wenn die Domain noch keinen
    Topic-Hub-Page hat.
    """
    if not topic.strip():
        return []
    topic_clean = topic.strip()
    # Schritt 1: Topic-Page finden.
    topic_row = conn.execute(
        "SELECT id FROM pages WHERE LOWER(title) = LOWER(?) AND type = 'topic' LIMIT 1",
        (topic_clean,),
    ).fetchone()
    if topic_row is not None:
        rows = conn.execute(
            """
            SELECT p.id, p.title, p.type, p.path, p.freshness
            FROM links l
            JOIN pages p ON p.id = l.from_page_id
            WHERE l.to_page_id = ? AND p.status = 'active'
            ORDER BY p.updated_at DESC
            LIMIT ?
            """,
            (topic_row["id"], int(limit)),
        ).fetchall()
        return [_row_to_entry(row) for row in rows]
    # Schritt 2: Title-Substring-Fallback.
    rows = conn.execute(
        "SELECT id, title, type, path, freshness FROM pages "
        "WHERE status = 'active' AND LOWER(title) LIKE ? "
        "ORDER BY updated_at DESC LIMIT ?",
        (f"%{topic_clean.lower()}%", int(limit)),
    ).fetchall()
    return [_row_to_entry(row) for row in rows]


def browse_by_collection(
    conn: sqlite3.Connection,
    collection: str,
    *,
    limit: int = 50,
) -> list[BrowseEntry]:
    """Pages, auf die die Collection-Page (per Wikilink) verweist."""
    if not collection.strip():
        return []
    collection_clean = collection.strip()
    coll_row = conn.execute(
        "SELECT id FROM pages WHERE LOWER(title) = LOWER(?) AND type = 'collection' LIMIT 1",
        (collection_clean,),
    ).fetchone()
    if coll_row is None:
        return []
    rows = conn.execute(
        """
        SELECT p.id, p.title, p.type, p.path, p.freshness
        FROM links l
        JOIN pages p ON p.id = l.to_page_id
        WHERE l.from_page_id = ? AND p.status = 'active'
        ORDER BY p.title
        LIMIT ?
        """,
        (coll_row["id"], int(limit)),
    ).fetchall()
    return [_row_to_entry(row) for row in rows]
