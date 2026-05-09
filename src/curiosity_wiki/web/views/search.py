"""Search-Page (HTML)."""

from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse

from curiosity_wiki import __version__
from curiosity_wiki.search import SearchError, search_pages
from curiosity_wiki.web.dependencies import get_conn
from curiosity_wiki.web.templating import get_templates
from curiosity_wiki.wiki.models import PageType

router = APIRouter()


@router.get("/search", response_class=HTMLResponse)
def search_view(
    request: Request,
    q: str = "",
    type: str | None = None,
    conn: sqlite3.Connection = Depends(get_conn),
) -> HTMLResponse:
    hits: list[dict[str, object]] = []
    if q.strip():
        try:
            results = search_pages(conn, q, page_type=type, limit=30)
            hits = [
                {
                    "page_id": h.page_id,
                    "title": h.title,
                    "type": h.page_type,
                    "freshness": h.freshness,
                    "rank": h.rank,
                    "snippet": h.snippet,
                    "slug": h.relative_path.rsplit("/", 1)[-1].removesuffix(".md"),
                    "path": h.relative_path,
                }
                for h in results
            ]
        except SearchError:
            hits = []
    context = {
        "request": request,
        "version": __version__,
        "q": q,
        "hits": hits,
        "filters": {"type": type or ""},
        "valid_types": sorted(p.value for p in PageType),
    }
    return get_templates().TemplateResponse(request, "search.html", context)
