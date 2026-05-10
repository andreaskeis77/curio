"""Read-Model-Builder (ADR-0016).

Jeder Builder liefert ein dict, das mit einem ``meta``-Block versehen und atomic
nach ``read_models/<name>.json`` geschrieben wird. ``search_documents`` ist
JSONL und wird zeilenweise serialisiert.

Konvention: jeder JSON-Read-Model hat das Format

    {
        "meta": { "schema_version": 1, "built_at": ..., ... },
        "data": <payload>,
    }

Atomic Write via ``curiosity_wiki.wiki.atomic.atomic_write_text``.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from pathlib import Path

from curiosity_wiki import __version__ as PACKAGE_VERSION
from curiosity_wiki.paths import VaultPaths, get_paths
from curiosity_wiki.wiki.aggregations import (
    collect_freshness_status,
    collect_open_questions,
)
from curiosity_wiki.wiki.atomic import atomic_write_text
from curiosity_wiki.wiki.frontmatter import FrontmatterError, parse_frontmatter

READ_MODEL_SCHEMA_VERSION = 1

# Dateinamen pro Read-Model.
READ_MODEL_FILES = {
    "site_index": "site_index.json",
    "graph": "graph.json",
    "search_documents": "search_documents.jsonl",
    "freshness_dashboard": "freshness_dashboard.json",
    "page_cards": "page_cards.json",
    "mobile_nav": "mobile_nav.json",
    "open_questions": "open_questions.json",
}


@dataclass
class RebuildResult:
    """Ergebnis eines vollen Rebuilds."""

    written: list[str] = field(default_factory=list)  # relative Pfade
    skipped: list[tuple[str, str]] = field(default_factory=list)  # (model, reason)
    pages_count: int = 0


@dataclass
class ReadModelStatus:
    """Build-Status eines Read-Models (fuer ``info``-CLI / Pre-Deploy-Gates)."""

    name: str
    path: str
    exists: bool
    schema_version: int | None = None
    built_at: str | None = None
    builder_version: str | None = None


def _now_iso() -> str:
    return datetime.now(tz=UTC).isoformat(timespec="seconds")


def _meta(extra: dict[str, object] | None = None) -> dict[str, object]:
    block: dict[str, object] = {
        "schema_version": READ_MODEL_SCHEMA_VERSION,
        "built_at": _now_iso(),
        "builder_version": PACKAGE_VERSION,
    }
    if extra:
        block.update(extra)
    return block


def _walk_wiki_files(wiki_root: Path) -> list[Path]:
    if not wiki_root.exists():
        return []
    return [
        path
        for path in wiki_root.rglob("*.md")
        if not any(part.startswith("_") or part == "README.md" for part in path.parts)
    ]


def _coerce_iso(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime | date):
        return value.isoformat()
    return str(value)


def _excerpt(body: str, *, max_chars: int = 800) -> str:
    """Erste sinnvollen Zeichen ohne Markdown-Header und ohne Claim-Marker-Zeilen."""
    lines: list[str] = []
    for line in body.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            continue
        if stripped.startswith("---"):
            continue
        if "claim:" in stripped and "source:" in stripped:
            continue
        lines.append(stripped)
        if sum(len(item) for item in lines) > max_chars:
            break
    text = " ".join(lines)
    if len(text) > max_chars:
        text = text[: max_chars - 1].rstrip() + "…"
    return text


def _short_snippet(body: str, *, max_chars: int = 300) -> str:
    return _excerpt(body, max_chars=max_chars)


def _frontmatter_for_pages(paths: VaultPaths) -> dict[str, dict[str, object]]:
    """Liest Frontmatter pro Page-ID, um Tags/Aliases/Body-Excerpt zur Hand zu haben."""
    out: dict[str, dict[str, object]] = {}
    for path in _walk_wiki_files(paths.wiki):
        try:
            text = path.read_text(encoding="utf-8")
            front, body = parse_frontmatter(text)
        except (OSError, FrontmatterError):
            continue
        page_id = front.data.get("id")
        if not page_id:
            continue
        out[str(page_id)] = {
            "frontmatter": front.data,
            "body": body,
        }
    return out


def build_site_index(conn: sqlite3.Connection) -> dict[str, object]:
    """Site-Index: alle Pages mit Status active."""
    rows = conn.execute(
        """
        SELECT id, title, slug, type, status, freshness, path, updated_at
        FROM pages
        WHERE status = 'active'
        ORDER BY updated_at DESC
        """
    ).fetchall()
    data = [
        {
            "id": row["id"],
            "title": row["title"],
            "slug": row["slug"],
            "type": row["type"],
            "status": row["status"],
            "freshness": row["freshness"] or "",
            "path": row["path"],
            "updated_at": row["updated_at"],
        }
        for row in rows
    ]
    return {"meta": _meta({"pages_count": len(data)}), "data": data}


def build_graph(conn: sqlite3.Connection) -> dict[str, object]:
    """Linkgraph: Knoten = Pages, Kanten = links-Tabelle."""
    nodes = [
        {
            "id": row["id"],
            "title": row["title"],
            "type": row["type"],
        }
        for row in conn.execute(
            "SELECT id, title, type FROM pages WHERE status = 'active'"
        ).fetchall()
    ]
    edges = [
        {
            "from": row["from_page_id"],
            "to": row["to_page_id"],
            "target_text": row["target_text"],
            "status": row["status"],
        }
        for row in conn.execute(
            """
            SELECT from_page_id, to_page_id, target_text, status
            FROM links
            """
        ).fetchall()
    ]
    return {
        "meta": _meta({"nodes_count": len(nodes), "edges_count": len(edges)}),
        "data": {"nodes": nodes, "edges": edges},
    }


def build_search_documents(
    conn: sqlite3.Connection,
    *,
    paths: VaultPaths,
) -> list[dict[str, object]]:
    """Pro Page ein Dokument fuer alternative Suchpfade.

    Liefert eine Liste; der Writer serialisiert sie als JSONL.
    """
    fronts = _frontmatter_for_pages(paths)
    rows = conn.execute(
        "SELECT id, title, type, slug, path FROM pages WHERE status = 'active'"
    ).fetchall()
    out: list[dict[str, object]] = []
    for row in rows:
        page_id = row["id"]
        front_block = fronts.get(page_id, {})
        body = str(front_block.get("body") or "")
        front = front_block.get("frontmatter") or {}
        tags = front.get("tags") if isinstance(front, dict) else None
        out.append(
            {
                "id": page_id,
                "title": row["title"],
                "type": row["type"],
                "slug": row["slug"],
                "path": row["path"],
                "tags": list(tags) if isinstance(tags, list) else [],
                "body_excerpt": _excerpt(body),
            }
        )
    return out


def build_freshness_dashboard(conn: sqlite3.Connection) -> dict[str, object]:
    """Aggregiert ueber ``collect_freshness_status`` plus Scout-Status (M7)."""
    report = collect_freshness_status(conn)

    def _entry_to_dict(entry) -> dict[str, object]:
        return {
            "page_id": entry.page_id,
            "title": entry.title,
            "page_type": entry.page_type,
            "path": entry.relative_path,
            "freshness": entry.freshness,
            "review_after": _coerce_iso(entry.review_after),
            "days_overdue": entry.days_overdue,
        }

    # Scout-Status: pro scout_id den letzten completed/skipped/failed-Lauf.
    scout_rows = conn.execute(
        """
        SELECT sr.scout_id, sr.id AS run_id, sr.started_at, sr.finished_at,
               sr.status, sr.proposals, sr.quarantined, sr.errors
        FROM scout_runs sr
        JOIN (
            SELECT scout_id, MAX(started_at) AS latest
            FROM scout_runs
            WHERE status != 'running'
            GROUP BY scout_id
        ) latest ON latest.scout_id = sr.scout_id AND latest.latest = sr.started_at
        ORDER BY sr.scout_id
        """
    ).fetchall()
    scouts = [
        {
            "scout_id": row["scout_id"],
            "last_run_id": row["run_id"],
            "last_started_at": row["started_at"],
            "last_finished_at": row["finished_at"],
            "last_status": row["status"],
            "last_proposals": int(row["proposals"] or 0),
            "last_quarantined": int(row["quarantined"] or 0),
            "last_errors": int(row["errors"] or 0),
        }
        for row in scout_rows
    ]

    data = {
        "overdue": [_entry_to_dict(e) for e in report.overdue],
        "due_within_7_days": [_entry_to_dict(e) for e in report.due_within_7_days],
        "volatile_without_schedule": [_entry_to_dict(e) for e in report.volatile_without_schedule],
        "scouts": scouts,
    }
    return {"meta": _meta({"buckets": list(data.keys())}), "data": data}


def build_page_cards(
    conn: sqlite3.Connection,
    *,
    paths: VaultPaths,
) -> dict[str, object]:
    """Page-Cards mit Snippet, Backlinks-Count, Freshness, Confidence."""
    fronts = _frontmatter_for_pages(paths)
    rows = conn.execute(
        """
        SELECT p.id, p.title, p.slug, p.type, p.path, p.freshness, p.confidence,
               p.updated_at,
               (SELECT COUNT(*) FROM links l WHERE l.to_page_id = p.id) AS backlink_count
        FROM pages p
        WHERE p.status = 'active'
        ORDER BY p.updated_at DESC
        """
    ).fetchall()
    cards = []
    for row in rows:
        page_id = row["id"]
        front_block = fronts.get(page_id, {})
        body = str(front_block.get("body") or "")
        front = front_block.get("frontmatter") or {}
        tags = front.get("tags") if isinstance(front, dict) else None
        why_interesting = ""
        if isinstance(front, dict):
            why_interesting = str(front.get("why_interesting") or "")
        cards.append(
            {
                "id": page_id,
                "title": row["title"],
                "slug": row["slug"],
                "type": row["type"],
                "path": row["path"],
                "freshness": row["freshness"] or "",
                "confidence": row["confidence"] or "",
                "updated_at": row["updated_at"],
                "tags": list(tags) if isinstance(tags, list) else [],
                "why_interesting": why_interesting,
                "snippet": _short_snippet(body),
                "backlink_count": int(row["backlink_count"] or 0),
            }
        )
    return {"meta": _meta({"cards_count": len(cards)}), "data": cards}


def build_mobile_nav(conn: sqlite3.Connection) -> dict[str, object]:
    """Mobile Navigation: Top-Topics, Collections, Recent Updates."""
    topics = [
        {"id": row["id"], "title": row["title"], "slug": row["slug"]}
        for row in conn.execute(
            "SELECT id, title, slug FROM pages WHERE status='active' AND type='topic' "
            "ORDER BY title LIMIT 30"
        ).fetchall()
    ]
    collections = [
        {"id": row["id"], "title": row["title"], "slug": row["slug"]}
        for row in conn.execute(
            "SELECT id, title, slug FROM pages WHERE status='active' AND type='collection' "
            "ORDER BY title LIMIT 30"
        ).fetchall()
    ]
    recent = [
        {
            "id": row["id"],
            "title": row["title"],
            "slug": row["slug"],
            "type": row["type"],
            "updated_at": row["updated_at"],
        }
        for row in conn.execute(
            "SELECT id, title, slug, type, updated_at FROM pages "
            "WHERE status='active' AND type != 'source' "
            "ORDER BY updated_at DESC LIMIT 10"
        ).fetchall()
    ]
    return {
        "meta": _meta({"topics_count": len(topics), "collections_count": len(collections)}),
        "data": {"topics": topics, "collections": collections, "recent": recent},
    }


def build_open_questions(paths: VaultPaths | None = None) -> dict[str, object]:
    """Open-Questions-Aggregation aus ``collect_open_questions``."""
    paths = paths or get_paths()
    items = collect_open_questions(paths=paths)
    data = [
        {
            "text": item.text,
            "page_id": item.page_id,
            "page_title": item.page_title,
            "page_path": item.page_path,
            "source": item.source,
        }
        for item in items
    ]
    return {"meta": _meta({"questions_count": len(data)}), "data": data}


def _write_json(target: Path, payload: dict[str, object]) -> None:
    atomic_write_text(target, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")


def _write_jsonl(target: Path, items: list[dict[str, object]]) -> None:
    body = "\n".join(json.dumps(item, ensure_ascii=False) for item in items)
    if body:
        body += "\n"
    atomic_write_text(target, body)


def rebuild_all(
    conn: sqlite3.Connection,
    *,
    paths: VaultPaths | None = None,
) -> RebuildResult:
    """Voller Rebuild aller Read-Models in ``read_models/``."""
    paths = paths or get_paths()
    paths.read_models.mkdir(parents=True, exist_ok=True)
    result = RebuildResult()
    pages_count = conn.execute("SELECT COUNT(*) AS n FROM pages WHERE status = 'active'").fetchone()
    result.pages_count = int(pages_count["n"]) if pages_count else 0

    for name, builder in (
        ("site_index", lambda: build_site_index(conn)),
        ("graph", lambda: build_graph(conn)),
        ("freshness_dashboard", lambda: build_freshness_dashboard(conn)),
        ("page_cards", lambda: build_page_cards(conn, paths=paths)),
        ("mobile_nav", lambda: build_mobile_nav(conn)),
        ("open_questions", lambda: build_open_questions(paths)),
    ):
        target = paths.read_models / READ_MODEL_FILES[name]
        try:
            payload = builder()
            _write_json(target, payload)
            result.written.append(str(target.relative_to(paths.root)))
        except Exception as exc:  # builder-Fehler nicht silent verschlucken
            result.skipped.append((name, f"{exc.__class__.__name__}: {exc}"))

    # search_documents.jsonl separat
    target = paths.read_models / READ_MODEL_FILES["search_documents"]
    try:
        items = build_search_documents(conn, paths=paths)
        _write_jsonl(target, items)
        result.written.append(str(target.relative_to(paths.root)))
    except Exception as exc:
        result.skipped.append(("search_documents", f"{exc.__class__.__name__}: {exc}"))

    return result


def read_model_status(paths: VaultPaths | None = None) -> list[ReadModelStatus]:
    """Status fuer jeden bekannten Read-Model (gebaut, Schema, Zeit)."""
    paths = paths or get_paths()
    out: list[ReadModelStatus] = []
    for name, filename in READ_MODEL_FILES.items():
        target = paths.read_models / filename
        if not target.exists():
            out.append(
                ReadModelStatus(name=name, path=str(target.relative_to(paths.root)), exists=False)
            )
            continue
        if filename.endswith(".jsonl"):
            # JSONL hat keinen Manifest-Header — wir nehmen mtime als Naeherung.
            mtime = datetime.fromtimestamp(target.stat().st_mtime, tz=UTC).isoformat(
                timespec="seconds"
            )
            out.append(
                ReadModelStatus(
                    name=name,
                    path=str(target.relative_to(paths.root)),
                    exists=True,
                    schema_version=None,
                    built_at=mtime,
                    builder_version=None,
                )
            )
            continue
        try:
            payload = json.loads(target.read_text(encoding="utf-8"))
            meta = payload.get("meta") or {}
            out.append(
                ReadModelStatus(
                    name=name,
                    path=str(target.relative_to(paths.root)),
                    exists=True,
                    schema_version=meta.get("schema_version"),
                    built_at=meta.get("built_at"),
                    builder_version=meta.get("builder_version"),
                )
            )
        except (OSError, json.JSONDecodeError):
            out.append(
                ReadModelStatus(name=name, path=str(target.relative_to(paths.root)), exists=True)
            )
    return out
