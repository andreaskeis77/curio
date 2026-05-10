-- Migration 0005
-- Tranche: M7
-- Zweck: Scout-Run-Audit-Spur (siehe ADR-0019)
-- Autor: Andreas Keis
-- Datum: 2026-05-09

CREATE TABLE IF NOT EXISTS scout_runs (
    id              TEXT    PRIMARY KEY,           -- sr_<ULID>
    scout_id        TEXT    NOT NULL,
    started_at      TEXT    NOT NULL,
    finished_at     TEXT,
    status          TEXT    NOT NULL,              -- running | completed | skipped | failed | crashed
    sources_seen    INTEGER NOT NULL DEFAULT 0,
    captured        INTEGER NOT NULL DEFAULT 0,
    skipped         INTEGER NOT NULL DEFAULT 0,
    proposals       INTEGER NOT NULL DEFAULT 0,
    quarantined     INTEGER NOT NULL DEFAULT 0,
    errors          INTEGER NOT NULL DEFAULT 0,
    log_path        TEXT,
    error_message   TEXT
);

CREATE INDEX IF NOT EXISTS idx_scout_runs_scout   ON scout_runs(scout_id);
CREATE INDEX IF NOT EXISTS idx_scout_runs_started ON scout_runs(started_at);
CREATE INDEX IF NOT EXISTS idx_scout_runs_status  ON scout_runs(status);
