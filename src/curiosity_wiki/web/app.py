"""FastAPI-App-Factory (M5, ADR-0015).

``create_app`` baut die App, registriert die JSON-API-Router und legt die
Vault-Pfade in ``app.state.paths`` ab. Die HTML-Views (M5c) werden hier
ebenfalls registriert.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

from curiosity_wiki import __version__
from curiosity_wiki.paths import VaultPaths, get_paths
from curiosity_wiki.web.api import api_router
from curiosity_wiki.web.health_deep import deep_health
from curiosity_wiki.web.templating import STATIC_DIR
from curiosity_wiki.web.views import views_router


def create_app(paths: VaultPaths | None = None) -> FastAPI:
    """Erstellt die App-Instanz. ``paths`` defaulted auf ``get_paths()``."""
    paths = paths or get_paths()
    app = FastAPI(
        title="Curiosity Wiki",
        version=__version__,
        description=(
            "Persoenliches, quellengestuetztes Wissenssystem. "
            "Read-only Web-UI ueber Wiki-Pages, Sources, Search."
        ),
    )
    app.state.paths = paths
    app.include_router(api_router)
    app.include_router(views_router)
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    @app.get("/healthz", response_class=PlainTextResponse, include_in_schema=False)
    def healthz() -> str:
        return "ok"

    @app.get("/healthz/deep", include_in_schema=False)
    def healthz_deep() -> JSONResponse:
        report = deep_health(paths)
        status_code = 200 if report["status"] in {"ok", "degraded"} else 503
        return JSONResponse(report, status_code=status_code)

    return app
