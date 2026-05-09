"""Pages-API: Liste, Detail."""

from __future__ import annotations

import sqlite3
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from curiosity_wiki.paths import VaultPaths
from curiosity_wiki.web.dependencies import get_conn, get_paths
from curiosity_wiki.wiki.frontmatter import FrontmatterError, parse_frontmatter
from curiosity_wiki.wiki.models import PageType
from curiosity_wiki.wiki.repository import LinkRepository, PageRepository

router = APIRouter(tags=["pages"])

_VALID_TYPES = {p.value for p in PageType}


def _page_to_dict(page) -> dict[str, Any]:
    return {
        "id": page.id,
        "title": page.title,
        "slug": page.slug,
        "type": page.page_type.value,
        "status": page.status.value,
        "freshness": page.freshness.value,
        "confidence": page.confidence.value,
        "path": page.relative_path,
        "updated_at": page.updated_at.isoformat(timespec="seconds"),
        "review_after": page.review_after.isoformat(timespec="seconds")
        if page.review_after
        else None,
    }


@router.get("/pages")
def list_pages(
    page_type: str | None = Query(None, alias="type", description="Filter PageType"),
    limit: int = Query(50, ge=1, le=500),
    conn: sqlite3.Connection = Depends(get_conn),
) -> dict[str, Any]:
    if page_type is not None and page_type not in _VALID_TYPES:
        raise HTTPException(status_code=400, detail=f"unknown page type: {page_type}")
    repo = PageRepository(conn)
    items = (
        repo.list_by_type(PageType(page_type), limit=limit)
        if page_type
        else repo.list_all(limit=limit)
    )
    return {"count": len(items), "items": [_page_to_dict(p) for p in items]}


@router.get("/pages/{page_id}")
def page_detail(
    page_id: str,
    paths: VaultPaths = Depends(get_paths),
    conn: sqlite3.Connection = Depends(get_conn),
) -> dict[str, Any]:
    repo = PageRepository(conn)
    page = repo.get(page_id)
    if page is None:
        raise HTTPException(status_code=404, detail=f"page not found: {page_id}")
    md_path = paths.root / page.relative_path
    body = ""
    frontmatter: dict[str, Any] = {}
    if md_path.exists():
        text = md_path.read_text(encoding="utf-8")
        try:
            front, body = parse_frontmatter(text)
            frontmatter = dict(front.data)
        except FrontmatterError:
            body = text
    backlinks = LinkRepository(conn).backlinks(page.id)
    backlink_pages: list[dict[str, str]] = []
    for back_id in backlinks:
        bp = repo.get(back_id)
        if bp is not None:
            backlink_pages.append({"id": bp.id, "title": bp.title, "path": bp.relative_path})
    return {
        **_page_to_dict(page),
        "frontmatter": frontmatter,
        "body_markdown": body,
        "backlinks": backlink_pages,
    }
