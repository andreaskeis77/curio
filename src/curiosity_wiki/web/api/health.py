"""Health-Endpoint."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from curiosity_wiki import __version__
from curiosity_wiki.paths import VaultPaths
from curiosity_wiki.read_models import read_model_status
from curiosity_wiki.web.dependencies import get_paths

router = APIRouter(tags=["health"])


@router.get("/health")
def health(paths: VaultPaths = Depends(get_paths)) -> dict[str, Any]:
    """Liveness + grundlegende Status-Indikatoren."""
    statuses = read_model_status(paths=paths)
    return {
        "status": "ok",
        "version": __version__,
        "registry_db_exists": paths.registry_db.exists(),
        "wiki_exists": paths.wiki.exists(),
        "read_models": [
            {
                "name": s.name,
                "exists": s.exists,
                "schema_version": s.schema_version,
                "built_at": s.built_at,
            }
            for s in statuses
        ],
    }
