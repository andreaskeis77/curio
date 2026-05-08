"""curiosity_wiki.registry — SQLite-Persistenz für operative Zustände.

Public API:

- ``connect(db_path)``  : Connection mit FK-Enforcement und WAL.
- ``migrate(conn)``     : alle Migrationen anwenden (idempotent).
- ``current_schema_version(conn)`` : zuletzt angewandte Version.
- ``check_schema(conn)`` : prüft Schema-Integrität (Stufe 3 Validation).

Tabellen-Repositories liegen in ``sources_repo``.
"""

from __future__ import annotations

from curiosity_wiki.registry.connection import (
    check_schema,
    connect,
    current_schema_version,
    migrate,
)

__all__ = [
    "check_schema",
    "connect",
    "current_schema_version",
    "migrate",
]
