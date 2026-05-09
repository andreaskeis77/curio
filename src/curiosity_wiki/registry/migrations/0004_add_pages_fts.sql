-- Migration 0004
-- Tranche: M4
-- Zweck: FTS5-Index ueber Wiki-Pages (siehe ADR-0014)
-- Autor: Andreas Keis
-- Datum: 2026-05-09

-- pages_fts: virtuelle FTS5-Tabelle, eigenstaendig (kein content=pages),
-- unicode61-Tokenizer mit Diacritic-Stripping fuer deutsche/franzoesische Texte.
CREATE VIRTUAL TABLE IF NOT EXISTS pages_fts USING fts5(
    page_id UNINDEXED,
    title,
    body,
    tags,
    why_interesting,
    tokenize = 'unicode61 remove_diacritics 1'
);
