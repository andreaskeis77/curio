"""FTS5-Index-Pflege fuer Wiki-Pages (ADR-0014).

Funktionen:

- ``index_page``: Eine Page in ``pages_fts`` einfuegen / aktualisieren.
- ``delete_page``: Eine Page aus ``pages_fts`` entfernen.
- ``rebuild_index_from_markdown``: Index komplett aus ``wiki/**/*.md`` neu
  erzeugen — das ist die Wahrheit nach manuellen Edits oder ``git pull``.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

from curiosity_wiki.paths import VaultPaths, get_paths
from curiosity_wiki.wiki.frontmatter import FrontmatterError, parse_frontmatter


@dataclass
class RebuildResult:
    """Ergebnis von ``rebuild_index_from_markdown``."""

    files_scanned: int = 0
    rows_written: int = 0
    skipped: list[tuple[str, str]] = field(default_factory=list)  # (path, reason)


def _tags_string(value: object) -> str:
    if isinstance(value, list):
        return " ".join(str(item) for item in value)
    if value is None:
        return ""
    return str(value)


def index_page(
    conn: sqlite3.Connection,
    *,
    page_id: str,
    title: str,
    body: str,
    tags: object = None,
    why_interesting: str = "",
) -> None:
    """Einfaches Upsert: alte Eintraege fuer ``page_id`` loeschen, dann insert."""
    conn.execute("DELETE FROM pages_fts WHERE page_id = ?", (page_id,))
    conn.execute(
        """
        INSERT INTO pages_fts (page_id, title, body, tags, why_interesting)
        VALUES (?, ?, ?, ?, ?)
        """,
        (page_id, title, body, _tags_string(tags), why_interesting),
    )


def delete_page(conn: sqlite3.Connection, page_id: str) -> None:
    """Eintrag aus dem Index entfernen."""
    conn.execute("DELETE FROM pages_fts WHERE page_id = ?", (page_id,))


def _walk_wiki_files(wiki_root: Path) -> list[Path]:
    """Alle .md-Files unter ``wiki/`` ohne ``_meta``/``README.md``."""
    if not wiki_root.exists():
        return []
    out: list[Path] = []
    for path in wiki_root.rglob("*.md"):
        if any(part.startswith("_") or part == "README.md" for part in path.parts):
            continue
        out.append(path)
    return out


def rebuild_index_from_markdown(
    conn: sqlite3.Connection, *, paths: VaultPaths | None = None
) -> RebuildResult:
    """Komplett neu aufbauen: ``DELETE FROM pages_fts``, dann alle Wiki-Files lesen."""
    paths = paths or get_paths()
    result = RebuildResult()
    conn.execute("DELETE FROM pages_fts")
    for path in _walk_wiki_files(paths.wiki):
        result.files_scanned += 1
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            result.skipped.append((str(path), f"read error: {exc}"))
            continue
        try:
            front, body = parse_frontmatter(text)
        except FrontmatterError as exc:
            result.skipped.append((str(path), f"frontmatter: {exc}"))
            continue
        page_id = str(front.data.get("id") or "")
        title = str(front.data.get("title") or "")
        if not page_id or not title:
            result.skipped.append((str(path), "missing id or title"))
            continue
        index_page(
            conn,
            page_id=page_id,
            title=title,
            body=body,
            tags=front.data.get("tags"),
            why_interesting=str(front.data.get("why_interesting") or ""),
        )
        result.rows_written += 1
    return result
