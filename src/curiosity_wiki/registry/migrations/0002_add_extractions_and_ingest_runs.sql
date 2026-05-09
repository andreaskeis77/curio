-- Migration 0002
-- Tranche: M2
-- Zweck: Extraktion, LLM-Runs, Prompts, Proposals, Quarantäne
-- Autor: Andreas Keis
-- Datum: 2026-05-08

-- Pro Source potentiell mehrere Extraktionsläufe (z.B. nach Library-Update)
CREATE TABLE IF NOT EXISTS extractions (
    id                  TEXT    PRIMARY KEY,
    source_id           TEXT    NOT NULL,
    extractor           TEXT    NOT NULL,    -- trafilatura | pypdf | passthrough | text | data
    extractor_version   TEXT    NOT NULL,
    input_sha256        TEXT    NOT NULL,
    output_path         TEXT,
    output_sha256       TEXT,
    output_chars        INTEGER,
    status              TEXT    NOT NULL,    -- extracted | failed | empty | quarantined
    started_at          TEXT    NOT NULL,
    finished_at         TEXT,
    warnings_json       TEXT,
    error_message       TEXT,
    FOREIGN KEY (source_id) REFERENCES sources(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_extractions_source       ON extractions(source_id);
CREATE INDEX IF NOT EXISTS idx_extractions_status       ON extractions(status);
CREATE INDEX IF NOT EXISTS idx_extractions_started      ON extractions(started_at);

-- Prompt-Registry (Datei-basiert, Tabelle für Run-Provenienz)
CREATE TABLE IF NOT EXISTS agent_prompts (
    prompt_id        TEXT    PRIMARY KEY,    -- z.B. ingest_v0_1
    prompt_hash      TEXT    NOT NULL,
    purpose          TEXT,
    schema_version   INTEGER NOT NULL DEFAULT 1,
    file_path        TEXT    NOT NULL,
    registered_at    TEXT    NOT NULL
);

-- Pro LLM-Call ein Eintrag (Run Evidence laut ADR-0010)
CREATE TABLE IF NOT EXISTS ingest_runs (
    id                TEXT    PRIMARY KEY,   -- run_<id>
    source_id         TEXT    NOT NULL,
    prompt_id         TEXT    NOT NULL,
    prompt_hash       TEXT    NOT NULL,
    provider          TEXT    NOT NULL,      -- mock | anthropic | openai
    model             TEXT,
    temperature       REAL,
    max_tokens        INTEGER,
    started_at        TEXT    NOT NULL,
    finished_at       TEXT,
    status            TEXT    NOT NULL,      -- running | completed | failed | quarantined
    token_usage_json  TEXT,
    proposal_id       TEXT,
    error_message     TEXT,
    FOREIGN KEY (source_id)  REFERENCES sources(id) ON DELETE CASCADE,
    FOREIGN KEY (prompt_id)  REFERENCES agent_prompts(prompt_id)
);

CREATE INDEX IF NOT EXISTS idx_ingest_runs_source   ON ingest_runs(source_id);
CREATE INDEX IF NOT EXISTS idx_ingest_runs_status   ON ingest_runs(status);
CREATE INDEX IF NOT EXISTS idx_ingest_runs_started  ON ingest_runs(started_at);

-- Proposals (Metadaten — Inhalt liegt in proposals/<run_id>/...)
CREATE TABLE IF NOT EXISTS proposals (
    id              TEXT    PRIMARY KEY,
    proposal_type   TEXT    NOT NULL,        -- ingest | link | refactor
    source_id       TEXT,
    run_id          TEXT,
    path            TEXT    NOT NULL,        -- relativer Pfad zum Proposal-Ordner
    status          TEXT    NOT NULL,        -- pending | approved | rejected | needs_changes | quarantined
    risk_level      TEXT,                    -- low | medium | high
    new_pages_count INTEGER NOT NULL DEFAULT 0,
    hard_facts_count INTEGER NOT NULL DEFAULT 0,
    open_questions_count INTEGER NOT NULL DEFAULT 0,
    confidence      TEXT,                    -- low | medium | high
    created_at      TEXT    NOT NULL,
    reviewed_at     TEXT,
    review_decision TEXT,
    FOREIGN KEY (source_id) REFERENCES sources(id) ON DELETE CASCADE,
    FOREIGN KEY (run_id)    REFERENCES ingest_runs(id)
);

CREATE INDEX IF NOT EXISTS idx_proposals_status     ON proposals(status);
CREATE INDEX IF NOT EXISTS idx_proposals_source     ON proposals(source_id);
CREATE INDEX IF NOT EXISTS idx_proposals_created    ON proposals(created_at);

-- Quarantäne-Fälle: First-Class-Modellierung von „etwas stimmt nicht"
CREATE TABLE IF NOT EXISTS quarantine_cases (
    id              TEXT    PRIMARY KEY,
    case_type       TEXT    NOT NULL,        -- prompt_injection | extraction_failed | source_policy_risk | claim_unverified | duplicate_page | stale_volatile_page | schema_violation
    severity        TEXT    NOT NULL,        -- low | medium | high
    source_id       TEXT,
    run_id          TEXT,
    proposal_id     TEXT,
    status          TEXT    NOT NULL,        -- open | resolved | suppressed | archived
    owner           TEXT,
    created_at      TEXT    NOT NULL,
    resolved_at     TEXT,
    evidence_json   TEXT,
    recommended_action TEXT,
    notes           TEXT,
    FOREIGN KEY (source_id)   REFERENCES sources(id)        ON DELETE SET NULL,
    FOREIGN KEY (run_id)      REFERENCES ingest_runs(id),
    FOREIGN KEY (proposal_id) REFERENCES proposals(id)      ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_quarantine_status   ON quarantine_cases(status);
CREATE INDEX IF NOT EXISTS idx_quarantine_type     ON quarantine_cases(case_type);
