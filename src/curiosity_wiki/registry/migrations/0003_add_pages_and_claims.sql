-- Migration 0003
-- Tranche: M3
-- Zweck: Wiki-Pages, Page-Sources, Claims, Links
-- Autor: Andreas Keis
-- Datum: 2026-05-09

-- Wiki-Pages: kanonische Repraesentation einer veroeffentlichten Seite
CREATE TABLE IF NOT EXISTS pages (
    id              TEXT    PRIMARY KEY,        -- page_<ULID>
    title           TEXT    NOT NULL,
    slug            TEXT    NOT NULL,
    path            TEXT    NOT NULL,           -- relativ zum Vault-Root
    type            TEXT    NOT NULL,           -- topic | place | person | recipe | method | ...
    status          TEXT    NOT NULL,           -- active | draft | archived
    freshness       TEXT,                       -- stable | periodic | volatile | personal
    last_checked    TEXT,
    review_after    TEXT,
    confidence      TEXT,                       -- low | medium | high
    schema_version  INTEGER NOT NULL DEFAULT 1,
    proposal_id     TEXT,                       -- woher kam die Page
    created_at      TEXT    NOT NULL,
    updated_at      TEXT    NOT NULL,
    FOREIGN KEY (proposal_id) REFERENCES proposals(id) ON DELETE SET NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_pages_slug_type ON pages(slug, type);
CREATE INDEX IF NOT EXISTS idx_pages_type             ON pages(type);
CREATE INDEX IF NOT EXISTS idx_pages_status           ON pages(status);
CREATE INDEX IF NOT EXISTS idx_pages_freshness        ON pages(freshness);
CREATE INDEX IF NOT EXISTS idx_pages_review_after     ON pages(review_after);

-- Verknuepfung Page -> Source(s) auf Page-Ebene (ergaenzend zu Claims)
CREATE TABLE IF NOT EXISTS page_sources (
    page_id    TEXT NOT NULL,
    source_id  TEXT NOT NULL,
    relation   TEXT NOT NULL DEFAULT 'primary', -- primary | supporting | derived
    PRIMARY KEY (page_id, source_id),
    FOREIGN KEY (page_id)   REFERENCES pages(id)    ON DELETE CASCADE,
    FOREIGN KEY (source_id) REFERENCES sources(id)
);

CREATE INDEX IF NOT EXISTS idx_page_sources_source ON page_sources(source_id);

-- Claims: harte Fakten mit Quellenbindung (ADR-0013)
CREATE TABLE IF NOT EXISTS claims (
    id              TEXT    PRIMARY KEY,
    page_id         TEXT    NOT NULL,
    claim_text      TEXT    NOT NULL,
    claim_type      TEXT    NOT NULL,           -- year | number | price | spec | quote | location | percent | other
    source_id       TEXT    NOT NULL,
    source_locator  TEXT,
    confidence      TEXT    NOT NULL,           -- low | medium | high
    verified_at     TEXT,
    proposal_id     TEXT,
    created_at      TEXT    NOT NULL,
    updated_at      TEXT    NOT NULL,
    FOREIGN KEY (page_id)     REFERENCES pages(id)     ON DELETE CASCADE,
    FOREIGN KEY (source_id)   REFERENCES sources(id),
    FOREIGN KEY (proposal_id) REFERENCES proposals(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_claims_page    ON claims(page_id);
CREATE INDEX IF NOT EXISTS idx_claims_source  ON claims(source_id);
CREATE INDEX IF NOT EXISTS idx_claims_type    ON claims(claim_type);

-- Links zwischen Pages (Wikilinks und Backlinks)
CREATE TABLE IF NOT EXISTS links (
    from_page_id  TEXT NOT NULL,
    to_page_id    TEXT,                         -- NULL wenn Ziel noch nicht existiert
    target_text   TEXT NOT NULL,                -- der originale Wikilink-Text
    link_type     TEXT NOT NULL DEFAULT 'wikilink',
    status        TEXT NOT NULL DEFAULT 'resolved', -- resolved | broken | external
    created_at    TEXT NOT NULL,
    FOREIGN KEY (from_page_id) REFERENCES pages(id) ON DELETE CASCADE,
    FOREIGN KEY (to_page_id)   REFERENCES pages(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_links_from   ON links(from_page_id);
CREATE INDEX IF NOT EXISTS idx_links_to     ON links(to_page_id);
CREATE INDEX IF NOT EXISTS idx_links_status ON links(status);

-- Lint-Runs und -Findings
CREATE TABLE IF NOT EXISTS lint_runs (
    id              TEXT PRIMARY KEY,
    started_at      TEXT NOT NULL,
    finished_at     TEXT,
    status          TEXT NOT NULL,             -- running | completed | failed
    findings_count  INTEGER NOT NULL DEFAULT 0,
    errors_count    INTEGER NOT NULL DEFAULT 0,
    warnings_count  INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS lint_findings (
    id              TEXT PRIMARY KEY,
    lint_run_id     TEXT NOT NULL,
    severity        TEXT NOT NULL,             -- error | warning | info
    finding_type    TEXT NOT NULL,             -- z.B. claim_missing_source, broken_wikilink
    page_id         TEXT,
    source_id       TEXT,
    file_path       TEXT,
    message         TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'open', -- open | acknowledged | fixed
    created_at      TEXT NOT NULL,
    FOREIGN KEY (lint_run_id) REFERENCES lint_runs(id) ON DELETE CASCADE,
    FOREIGN KEY (page_id)     REFERENCES pages(id)     ON DELETE SET NULL,
    FOREIGN KEY (source_id)   REFERENCES sources(id)   ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_lint_findings_run      ON lint_findings(lint_run_id);
CREATE INDEX IF NOT EXISTS idx_lint_findings_severity ON lint_findings(severity);
CREATE INDEX IF NOT EXISTS idx_lint_findings_type     ON lint_findings(finding_type);
