"""Tests für Registry-Connection und Migration-Runner."""

from __future__ import annotations

from pathlib import Path

import pytest

from curiosity_wiki.registry import (
    check_schema,
    connect,
    current_schema_version,
    migrate,
)
from curiosity_wiki.registry.connection import (
    REQUIRED_TABLES,
    MigrationError,
    discover_migrations,
)


def test_discover_migrations_finds_initial() -> None:
    migrations = discover_migrations()
    assert migrations, "no migration files discovered"
    versions = [m[0] for m in migrations]
    assert versions == sorted(versions)
    assert versions[0] == 1


def test_fresh_state_migrates_clean(tmp_path: Path) -> None:
    db_path = tmp_path / "fresh.sqlite"
    expected_versions = [v for v, _, _ in discover_migrations()]
    with connect(db_path) as conn:
        applied = migrate(conn)
        assert applied == expected_versions
        assert current_schema_version(conn) == max(expected_versions)
        ok, findings = check_schema(conn)
        assert ok, findings


def test_evolved_state_is_idempotent(tmp_path: Path) -> None:
    db_path = tmp_path / "evolved.sqlite"
    expected_max = max(v for v, _, _ in discover_migrations())
    with connect(db_path) as conn:
        migrate(conn)
        assert migrate(conn) == [], "second migrate should be a no-op"
        assert current_schema_version(conn) == expected_max


def test_required_tables_exist(tmp_path: Path) -> None:
    db_path = tmp_path / "tables.sqlite"
    with connect(db_path) as conn:
        migrate(conn)
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        ).fetchall()
        names = {row["name"] for row in rows}
        for table in REQUIRED_TABLES:
            assert table in names


def test_check_schema_reports_missing_when_no_migration(tmp_path: Path) -> None:
    db_path = tmp_path / "empty.sqlite"
    with connect(db_path) as conn:
        ok, findings = check_schema(conn)
        assert not ok
        assert any("schema_version is 0" in f for f in findings)


def test_migration_error_for_invalid_sql(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Bei kaputtem Migration-File wird eine MigrationError geworfen."""
    bad_sql = tmp_path / "0001_broken.sql"
    bad_sql.write_text("CREATE TABLE garbled (;;;", encoding="utf-8")

    import curiosity_wiki.registry.connection as conn_module

    monkeypatch.setattr(conn_module, "MIGRATIONS_DIR", tmp_path)

    db_path = tmp_path / "broken.sqlite"
    with connect(db_path) as conn, pytest.raises(MigrationError):
        migrate(conn)
