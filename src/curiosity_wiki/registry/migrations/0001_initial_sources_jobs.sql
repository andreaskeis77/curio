-- Migration 0001
-- Tranche: M1
-- Zweck: Initiale Tabellen für Source Capture und Jobs
-- Autor: Andreas Keis
-- Datum: 2026-05-08

-- Schema-Versionierung selbst
CREATE TABLE IF NOT EXISTS schema_meta (
    schema_version INTEGER PRIMARY KEY,
    applied_at     TEXT    NOT NULL,
    description    TEXT
);

-- Sources: kanonische Repräsentation einer erfassten Quelle
CREATE TABLE IF NOT EXISTS sources (
    id              TEXT    PRIMARY KEY,
    title           TEXT,
    source_type     TEXT    NOT NULL,    -- web | pdf | file | note | data | screenshot
    original_url    TEXT,
    canonical_url   TEXT,
    captured_at     TEXT    NOT NULL,
    raw_path        TEXT    NOT NULL,
    extracted_path  TEXT,
    sha256          TEXT    NOT NULL,
    bytes           INTEGER,
    content_type    TEXT,
    language        TEXT,
    access          TEXT    NOT NULL,    -- public | private | paywalled | own_note
    copyright_risk  TEXT    NOT NULL,    -- low | medium | high
    reliability     TEXT    NOT NULL,    -- official | expert | journalistic | commercial | personal | unknown
    llm_allowed     INTEGER NOT NULL DEFAULT 1,
    status          TEXT    NOT NULL,    -- captured | extracted | classified | proposal_created | indexed | failed | quarantined
    why_interesting TEXT    NOT NULL,
    license_note    TEXT,
    created_at      TEXT    NOT NULL,
    updated_at      TEXT    NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_sources_url        ON sources(original_url);
CREATE INDEX IF NOT EXISTS idx_sources_sha256     ON sources(sha256);
CREATE INDEX IF NOT EXISTS idx_sources_status     ON sources(status);
CREATE INDEX IF NOT EXISTS idx_sources_type       ON sources(source_type);
CREATE INDEX IF NOT EXISTS idx_sources_captured   ON sources(captured_at);

-- Source-Snapshots: bei mehrfachem Re-Capture derselben URL/Datei mehrere Versionen
CREATE TABLE IF NOT EXISTS source_snapshots (
    id            TEXT    PRIMARY KEY,
    source_id     TEXT    NOT NULL,
    path          TEXT    NOT NULL,
    sha256        TEXT    NOT NULL,
    bytes         INTEGER,
    content_type  TEXT,
    captured_at   TEXT    NOT NULL,
    FOREIGN KEY (source_id) REFERENCES sources(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_snapshots_source   ON source_snapshots(source_id);
CREATE INDEX IF NOT EXISTS idx_snapshots_sha256   ON source_snapshots(sha256);

-- Jobs: hintergründige Verarbeitungs-Aufgaben (Extraction, Ingest, Lint, ...)
CREATE TABLE IF NOT EXISTS jobs (
    id             TEXT    PRIMARY KEY,
    job_type       TEXT    NOT NULL,
    target_id      TEXT,
    status         TEXT    NOT NULL,    -- queued | running | completed | failed | cancelled
    created_at     TEXT    NOT NULL,
    started_at     TEXT,
    finished_at    TEXT,
    error_message  TEXT,
    retry_count    INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_jobs_status        ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_type_target   ON jobs(job_type, target_id);
