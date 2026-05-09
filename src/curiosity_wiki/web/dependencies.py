"""FastAPI-Dependencies: VaultPaths und SQLite-Connections per Request.

Wir oeffnen pro Request eine eigene Connection — SQLite-Connections sind nicht
thread-safe ueber Connection-Boundaries hinweg, und FastAPI laeuft synchron in
Worker-Threads.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator

from fastapi import Depends, HTTPException, Request

from curiosity_wiki.paths import VaultPaths
from curiosity_wiki.registry import connect


def get_paths(request: Request) -> VaultPaths:
    """Liefert die VaultPaths, die beim App-Start gesetzt wurden."""
    paths = getattr(request.app.state, "paths", None)
    if paths is None:
        raise HTTPException(status_code=500, detail="App not initialized: paths missing")
    return paths


def get_conn(paths: VaultPaths = Depends(get_paths)) -> Iterator[sqlite3.Connection]:
    """Per-Request SQLite-Connection mit FK-Enforcement."""
    if not paths.registry_db.exists():
        raise HTTPException(
            status_code=503,
            detail="Registry not initialized. Run 'curiosity registry init' first.",
        )
    conn = connect(paths.registry_db)
    try:
        yield conn
    finally:
        conn.close()
