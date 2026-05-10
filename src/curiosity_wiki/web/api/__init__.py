"""curiosity_wiki.web.api — JSON-API-Routen."""

from __future__ import annotations

from fastapi import APIRouter

from curiosity_wiki.web.api import (
    browse,
    health,
    lint,
    pages,
    proposals,
    scouts,
    search,
    sources,
)

api_router = APIRouter(prefix="/api")
api_router.include_router(health.router)
api_router.include_router(pages.router)
api_router.include_router(sources.router)
api_router.include_router(search.router)
api_router.include_router(browse.router)
api_router.include_router(proposals.router)
api_router.include_router(lint.router)
api_router.include_router(scouts.router)

__all__ = ["api_router"]
