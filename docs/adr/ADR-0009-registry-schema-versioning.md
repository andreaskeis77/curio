# ADR-0009: Registry-Schema-Versionierung

- **Status:** Accepted
- **Datum:** 2026-05-08
- **Tranche:** M1 — Registry Spine

## Kontext

Die SQLite-Registry wächst über Phasen mit:

- M1: `sources`, `source_snapshots`, `jobs`, `schema_meta`.
- M2: `extractions`, `agent_prompts`, `agent_runs`, `ingest_runs`, `quarantine_cases`.
- M3: `pages`, `claims`, `page_sources`, `proposals`, `proposal_changes`, `reviews`.
- M4: `links`, `lint_runs`, `lint_findings`, `search_index_runs`, `freshness_tasks`.
- Später: weitere Erweiterungen pro Tranche.

Schema-Änderungen müssen reproduzierbar, nachvollziehbar, und sowohl auf **Fresh State** als auch auf **Evolved State** anwendbar sein.

## Optionen

- **A) Manuelle Schema-Datei pro Version.** Einfach, aber Drift-anfällig.
- **B) Migration-Tool (Alembic/yoyo).** Mächtig, aber Overhead für persönliches Projekt.
- **C) Eigener schlanker Migration-Runner mit nummerierten SQL-Files.** Klein, deterministisch, ausreichend.

## Entscheidung

**Option C: Eigener Migration-Runner.**

- Migrations als nummerierte `.sql`-Dateien unter `src/curiosity_wiki/registry/migrations/`.
- Format: `0001_initial_sources_jobs.sql`, `0002_add_extractions.sql`, …
- Tabelle `schema_meta` speichert die zuletzt angewandte Version.
- Migration-Runner ist idempotent: Wendet nur Migrationen an, deren Nummer höher als `schema_version` ist.
- Migrationen sind **einseitig** (vorwärts) — kein Auto-Downgrade. Rollback erfolgt über Backup-Restore.
- Jede Migration ist in einer Transaktion gewrapped.

## Begründung

- **Klein bleibt klein.** Kein zusätzliches Tool, keine zusätzliche Konfiguration.
- **Deterministisch.** SQL-Dateien sind diff-bar in Git.
- **Reviewbar.** Schema-Änderungen sind sofort sichtbar.
- **Fresh-State-fähig.** Ein leerer Vault läuft alle Migrationen der Reihe nach.
- **Evolved-State-fähig.** Eine bestehende Registry läuft nur die noch fehlenden Migrationen.
- **NEW NFL Lesson:** Layer-Modell ist explizit, Schema ist Teil des Engineering-Vertrags.

## Konsequenzen

### Positiv

- Klare Trennung zwischen Code (Python) und Daten-Schema (SQL).
- Schema-Änderung ist eine eigene Tranche.
- Tests können beide Zustände prüfen.

### Negativ

- **Kein Auto-Downgrade.** Wenn eine Migration fehlerhaft ist, muss aus Backup wiederhergestellt werden.
- **Manuelles Schreiben** der `.sql`-Dateien — ORM-Auto-Migration entfällt.

### Risiken und Mitigationen

| Risiko | Mitigation |
|---|---|
| Migration scheitert mittendrin | Transaktionaler Wrap pro Migration; bei Fehler: Rollback und Stop |
| Schema-Drift zwischen Code und DB | `registry check` validiert Schema-Version und kritische Tabellen-Felder |
| Mehrere Migrationen mit Konflikt-Ordnung | Numerische Sortierung erzwingt Reihenfolge |
| Versehentliches Editieren einer alten Migration | Migration-Files sind nach Akzeptanz **immutable** — neue Migration anhängen |

## Konvention

```text
src/curiosity_wiki/registry/migrations/
  0001_initial_sources_jobs.sql       # M1
  0002_add_extractions.sql            # M2 (geplant)
  0003_add_proposals_and_pages.sql    # M3 (geplant)
  ...
```

Jede `.sql`-Datei beginnt mit einem Kommentar:

```sql
-- Migration 0001
-- Tranche: M1
-- Zweck: Initiale Tabellen für Source Capture und Jobs
-- Autor: Andreas Keis
-- Datum: 2026-05-08
```

## Verweise

- [ADR-0001](ADR-0001-markdown-plus-sqlite-registry.md) — Markdown + SQLite Registry
- [ROADMAP](../ROADMAP.md) — M1 Registry Spine
- [VALIDATION_PROTOCOL](../VALIDATION_PROTOCOL.md) — Stufe 3 Schema-/Registry-Gate
