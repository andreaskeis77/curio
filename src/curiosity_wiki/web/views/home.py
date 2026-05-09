"""Home-Dashboard."""

from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse

from curiosity_wiki import __version__
from curiosity_wiki.browse import browse_random
from curiosity_wiki.paths import VaultPaths
from curiosity_wiki.sources import SourceRepository
from curiosity_wiki.web.dependencies import get_conn, get_paths
from curiosity_wiki.web.templating import get_templates
from curiosity_wiki.wiki.aggregations import (
    collect_freshness_status,
    collect_open_questions,
)
from curiosity_wiki.wiki.repository import PageRepository

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
def home(
    request: Request,
    conn: sqlite3.Connection = Depends(get_conn),
    paths: VaultPaths = Depends(get_paths),
) -> HTMLResponse:
    pages_count = conn.execute("SELECT COUNT(*) AS n FROM pages WHERE status='active'").fetchone()
    sources_count = SourceRepository(conn).count()
    open_questions = collect_open_questions(paths=paths)
    freshness = collect_freshness_status(conn)
    random_walk_entries = browse_random(conn, limit=6)
    random_cards = [
        {
            "page_id": e.page_id,
            "title": e.title,
            "type": e.page_type,
            "freshness": e.freshness,
            "slug": e.relative_path.split("/")[-1].removesuffix(".md"),
            "path": e.relative_path,
            "snippet": "",
            "why_interesting": "",
        }
        for e in random_walk_entries
    ]

    # Pages werden im Frontmatter mit slug gespeichert; wir holen die slug-attrs aus der DB.
    page_repo = PageRepository(conn)
    by_id = {p.id: p for p in page_repo.list_all(limit=500)}
    for card in random_cards:
        page = by_id.get(card["page_id"])
        if page is not None:
            card["slug"] = page.slug
            card["why_interesting"] = page.why_interesting

    freshness_data = {
        "overdue": [
            {
                "page_id": e.page_id,
                "title": e.title,
                "slug": _slug_from_path(e.relative_path),
                "review_after": e.review_after.isoformat() if e.review_after else "",
                "days_overdue": e.days_overdue,
                "path": e.relative_path,
            }
            for e in freshness.overdue[:10]
        ],
        "due_within_7_days": [
            {
                "page_id": e.page_id,
                "title": e.title,
                "slug": _slug_from_path(e.relative_path),
                "path": e.relative_path,
            }
            for e in freshness.due_within_7_days[:10]
        ],
    }

    context = {
        "request": request,
        "version": __version__,
        "stats": {
            "pages": int(pages_count["n"]) if pages_count else 0,
            "sources": sources_count,
            "open_questions": len(open_questions),
            "overdue": len(freshness.overdue),
        },
        "random_walk": random_cards,
        "open_questions": [
            {"text": q.text, "page_title": q.page_title} for q in open_questions[:8]
        ],
        "freshness": freshness_data,
    }
    return get_templates().TemplateResponse(request, "home.html", context)


def _slug_from_path(rel_path: str) -> str:
    """``wiki/topics/foo.md`` -> ``foo``."""
    name = rel_path.rsplit("/", 1)[-1]
    return name.removesuffix(".md")
