"""Deep-Health-Check fuer Pre-Deploy-Verifikation (M6, ADR-0017)."""

from __future__ import annotations

import sqlite3
from typing import Any

from curiosity_wiki import __version__
from curiosity_wiki.paths import VaultPaths
from curiosity_wiki.read_models import READ_MODEL_FILES, read_model_status
from curiosity_wiki.registry import current_schema_version


def deep_health(paths: VaultPaths) -> dict[str, Any]:
    """Detailierter Health-Report mit Status ``ok | degraded | down``.

    - ``down``: kritisches System fehlt (Registry, FTS5).
    - ``degraded``: Read-Models fehlen oder veraltet, aber Web kann antworten.
    - ``ok``: alles bereit.
    """
    checks: dict[str, dict[str, Any]] = {}
    status = "ok"

    # 1. Registry erreichbar
    if not paths.registry_db.exists():
        checks["registry"] = {"ok": False, "detail": "registry_db_missing"}
        status = "down"
        return _envelope(status, checks)
    try:
        conn = sqlite3.connect(str(paths.registry_db))
        conn.row_factory = sqlite3.Row
        version = current_schema_version(conn)
        checks["registry"] = {"ok": version > 0, "schema_version": version}
        if version <= 0:
            status = "down"

        # 2. FTS5-Tabelle vorhanden
        fts_row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='pages_fts'"
        ).fetchone()
        checks["fts5"] = {"ok": fts_row is not None}
        if fts_row is None:
            status = "down"

        # 3. Wiki-Verzeichnis vorhanden (Fehlen ist degraded, nicht down — UI kann antworten).
        checks["wiki"] = {"ok": paths.wiki.exists()}
        if not paths.wiki.exists() and status == "ok":
            status = "degraded"

        # 4. Pages-Count (informativ)
        pages_count = conn.execute("SELECT COUNT(*) AS n FROM pages").fetchone()
        checks["pages_count"] = {
            "ok": True,
            "value": int(pages_count["n"]) if pages_count else 0,
        }
        conn.close()
    except sqlite3.Error as exc:
        checks["registry"] = {"ok": False, "detail": f"sqlite_error: {exc}"}
        status = "down"
        return _envelope(status, checks)

    # 5. Read-Models existieren
    rm_statuses = {s.name: s for s in read_model_status(paths=paths)}
    rm_missing = [name for name in READ_MODEL_FILES if not rm_statuses[name].exists]
    rm_check: dict[str, Any] = {
        "ok": not rm_missing,
        "missing": rm_missing,
        "built": {
            name: rm_statuses[name].built_at
            for name in READ_MODEL_FILES
            if rm_statuses[name].exists
        },
    }
    checks["read_models"] = rm_check
    if rm_missing and status == "ok":
        status = "degraded"

    return _envelope(status, checks)


def _envelope(status: str, checks: dict[str, dict[str, Any]]) -> dict[str, Any]:
    return {
        "status": status,
        "version": __version__,
        "checks": checks,
    }
