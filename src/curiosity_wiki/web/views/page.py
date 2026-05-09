"""Page-Reader: /p/<slug>."""

from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse

from curiosity_wiki import __version__
from curiosity_wiki.paths import VaultPaths
from curiosity_wiki.sources import SourceRepository
from curiosity_wiki.web.dependencies import get_conn, get_paths
from curiosity_wiki.web.templating import get_templates, render_body_with_links
from curiosity_wiki.wiki.frontmatter import FrontmatterError, parse_frontmatter
from curiosity_wiki.wiki.repository import LinkRepository, PageRepository

router = APIRouter()


@router.get("/p/{slug}", response_class=HTMLResponse)
def page_view(
    slug: str,
    request: Request,
    conn: sqlite3.Connection = Depends(get_conn),
    paths: VaultPaths = Depends(get_paths),
) -> HTMLResponse:
    row = conn.execute(
        "SELECT id, title, slug, type, status, freshness, confidence, review_after, path "
        "FROM pages WHERE slug = ? AND status = 'active' LIMIT 1",
        (slug,),
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail=f"page not found: {slug}")

    md_path = paths.root / row["path"]
    body_md = ""
    frontmatter: dict[str, object] = {}
    if md_path.exists():
        text = md_path.read_text(encoding="utf-8")
        try:
            front, body_md = parse_frontmatter(text)
            frontmatter = dict(front.data)
        except FrontmatterError:
            body_md = text

    page_payload = {
        "id": row["id"],
        "title": row["title"],
        "slug": row["slug"],
        "type": row["type"],
        "freshness": row["freshness"] or "",
        "confidence": row["confidence"] or "",
        "review_after": (row["review_after"] or "").split("T")[0],
        "frontmatter": frontmatter,
    }

    body_html = render_body_with_links(body_md, conn)

    # Backlinks
    page_repo = PageRepository(conn)
    backlinks = LinkRepository(conn).backlinks(row["id"])
    backlink_pages = []
    for back_id in backlinks:
        bp = page_repo.get(back_id)
        if bp is not None:
            backlink_pages.append(
                {"id": bp.id, "title": bp.title, "slug": bp.slug, "path": bp.relative_path}
            )

    # Sources from page_sources -> sources
    source_rows = conn.execute(
        """
        SELECT s.id, s.title, s.source_type, s.access, s.original_url
        FROM page_sources ps
        JOIN sources s ON s.id = ps.source_id
        WHERE ps.page_id = ?
        """,
        (row["id"],),
    ).fetchall()
    source_repo = SourceRepository(conn)
    source_payloads = []
    for src_row in source_rows:
        source_payloads.append(
            {
                "id": src_row["id"],
                "title": src_row["title"] or src_row["id"],
                "type": src_row["source_type"],
                "access": src_row["access"],
                "original_url": src_row["original_url"],
            }
        )
    if not source_payloads and frontmatter.get("sources"):
        for src_id in frontmatter.get("sources") or []:
            src = source_repo.get(str(src_id))
            if src is not None:
                source_payloads.append(
                    {
                        "id": src.id,
                        "title": src.title or src.id,
                        "type": src.source_type.value,
                        "access": src.access.value,
                        "original_url": src.original_url,
                    }
                )

    context = {
        "request": request,
        "version": __version__,
        "page": page_payload,
        "body_html": body_html,
        "backlinks": backlink_pages,
        "sources": source_payloads,
    }
    return get_templates().TemplateResponse(request, "page.html", context)
