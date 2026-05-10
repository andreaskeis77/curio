"""Registry connection und Migration-Runner.

Schema-Versionierung gemäß ADR-0009: nummerierte ``.sql``-Dateien unter
``migrations/``, idempotent angewendet, in Transaktionen gewrapped.
"""

from __future__ import annotations

import re
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

MIGRATIONS_DIR = Path(__file__).parent / "migrations"
MIGRATION_PATTERN = re.compile(r"^(\d{4})_(.+)\.sql$")

# Tabellen, die nach erfolgreicher Migration zwingend existieren müssen.
# FTS5-Virtual-Tabellen erscheinen in ``sqlite_master`` ebenfalls mit ``type='table'``.
REQUIRED_TABLES = {
    "schema_meta",
    "sources",
    "source_snapshots",
    "jobs",
    "extractions",
    "agent_prompts",
    "ingest_runs",
    "proposals",
    "quarantine_cases",
    "pages",
    "page_sources",
    "claims",
    "links",
    "lint_runs",
    "lint_findings",
    "pages_fts",
    "scout_runs",
}


class MigrationError(RuntimeError):
    """Wird geworfen, wenn eine Migration fehlschlägt oder Drift erkannt wird."""


def connect(db_path: Path) -> sqlite3.Connection:
    """SQLite-Connection mit Foreign-Key-Enforcement und WAL.

    Verzeichnis wird erstellt, falls es fehlt.
    """
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path), isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def discover_migrations() -> list[tuple[int, str, Path]]:
    """Alle Migrations-Dateien in numerischer Reihenfolge."""
    found: list[tuple[int, str, Path]] = []
    if not MIGRATIONS_DIR.exists():
        return found
    for path in MIGRATIONS_DIR.iterdir():
        if not path.is_file() or path.suffix != ".sql":
            continue
        match = MIGRATION_PATTERN.match(path.name)
        if not match:
            continue
        version = int(match.group(1))
        name = match.group(2)
        found.append((version, name, path))
    found.sort(key=lambda item: item[0])
    return found


def current_schema_version(conn: sqlite3.Connection) -> int:
    """Höchste in ``schema_meta`` eingetragene Version. 0, wenn Tabelle fehlt."""
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_meta'"
    ).fetchone()
    if row is None:
        return 0
    cur = conn.execute("SELECT MAX(schema_version) AS v FROM schema_meta")
    result = cur.fetchone()
    return int(result["v"]) if result and result["v"] is not None else 0


def migrate(conn: sqlite3.Connection) -> list[int]:
    """Wendet ausstehende Migrationen an. Liefert die angewandten Versionen.

    Idempotent: bei vollständig migriertem Schema kein Side Effect.
    Migrationen verwenden ``CREATE ... IF NOT EXISTS``, sodass ein
    fehlgeschlagener Lauf gefahrlos wiederholt werden kann. Der Eintrag
    in ``schema_meta`` erfolgt nur bei erfolgreicher SQL-Ausführung.
    """
    applied: list[int] = []
    migrations = discover_migrations()
    if not migrations:
        return applied
    current = current_schema_version(conn)
    for version, name, path in migrations:
        if version <= current:
            continue
        sql = path.read_text(encoding="utf-8")
        try:
            conn.executescript(sql)
            conn.execute(
                "INSERT INTO schema_meta(schema_version, applied_at, description) VALUES (?, ?, ?)",
                (version, datetime.now(tz=UTC).isoformat(timespec="seconds"), name),
            )
        except sqlite3.Error as exc:
            raise MigrationError(f"Migration {version:04d}_{name} failed: {exc}") from exc
        applied.append(version)
    return applied


def check_schema(conn: sqlite3.Connection) -> tuple[bool, list[str]]:
    """Validiert Schema-Integrität.

    Liefert ``(ok, findings)``. ``ok`` ist ``True`` nur wenn keine
    Findings erzeugt wurden.
    """
    findings: list[str] = []

    version = current_schema_version(conn)
    if version == 0:
        findings.append("schema_version is 0 — no migrations applied")

    existing_tables = {
        row["name"]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        ).fetchall()
    }
    for table in REQUIRED_TABLES:
        if table not in existing_tables:
            findings.append(f"required table missing: {table}")

    integrity = conn.execute("PRAGMA integrity_check").fetchone()
    if integrity is None or integrity[0] != "ok":
        findings.append(f"integrity_check failed: {integrity}")

    return (not findings, findings)
