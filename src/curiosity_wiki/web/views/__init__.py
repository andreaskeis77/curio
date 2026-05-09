"""HTML-Views (Jinja2-Templates, M5c)."""

from __future__ import annotations

from fastapi import APIRouter

from curiosity_wiki.web.views import home, page, search, source

views_router = APIRouter()
views_router.include_router(home.router)
views_router.include_router(page.router)
views_router.include_router(search.router)
views_router.include_router(source.router)

__all__ = ["views_router"]
