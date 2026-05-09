"""Source-Page (HTML)."""

from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse

from curiosity_wiki import __version__
from curiosity_wiki.sources import SourceRepository
from curiosity_wiki.web.dependencies import get_conn
from curiosity_wiki.web.templating import get_templates

router = APIRouter()


@router.get("/s/{source_id}", response_class=HTMLResponse)
def source_view(
    source_id: str,
    request: Request,
    conn: sqlite3.Connection = Depends(get_conn),
) -> HTMLResponse:
    source = SourceRepository(conn).get(source_id)
    if source is None:
        raise HTTPException(status_code=404, detail=f"source not found: {source_id}")
    payload = {
        "id": source.id,
        "title": source.title,
        "type": source.source_type.value,
        "access": source.access.value,
        "copyright_risk": source.copyright_risk.value,
        "reliability": source.reliability.value,
        "status": source.status.value,
        "captured_at": source.captured_at.isoformat(timespec="seconds"),
        "language": source.language or "",
        "original_url": source.original_url,
        "sha256": source.sha256,
        "raw_path": source.raw_path,
        "why_interesting": source.why_interesting,
    }
    context = {"request": request, "version": __version__, "source": payload}
    return get_templates().TemplateResponse(request, "source.html", context)
