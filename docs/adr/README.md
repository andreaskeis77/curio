# Architecture Decision Records (ADRs)

ADRs dokumentieren wichtige Architekturentscheidungen mit Kontext, Optionen und Begründung. Sie sind nach Akzeptanz **unveränderlich**; Änderungen erfolgen über neue ADRs, die alte als „Superseded by ADR-XXXX" markieren.

## Format

Jedes ADR hat:

- **Status:** Proposed | Accepted | Superseded | Deprecated
- **Datum:** YYYY-MM-DD
- **Kontext:** Was war das Problem?
- **Entscheidung:** Was wurde entschieden?
- **Begründung:** Warum?
- **Konsequenzen:** Was bedeutet das?

## Aktive ADRs

| Nr. | Titel | Status |
|---|---|---|
| 0001 | Markdown plus SQLite Registry | Accepted |
| 0002 | Immutable Raw Sources | Accepted |
| 0003 | Agent Proposals statt Direktwrites | Accepted |
| 0004 | Read-only VPS first | Accepted |
| 0005 | Web UI mit Read Models | Accepted |
| 0006 | Source Policy and Copyright Boundaries | Accepted |
| 0007 | LLM Client Wrapper und Prompt Registry | Accepted |
| 0008 | Sucharchitektur in Stufen | Accepted |
| 0009 | Registry-Schema-Versionierung | Accepted |
| 0010 | LLM-Client-Wrapper-Implementierung | Accepted |
| 0011 | Extraction-Strategie und Fallbacks | Accepted |
| 0012 | Atomic Writes und Git-Commit-Strategie | Accepted |
| 0013 | Claim-Provenienz-Modell | Accepted |
| 0014 | Sucharchitektur Stufe 1 — FTS5-Implementierung | Accepted |

## Geplante ADRs (in zukünftigen Tranchen)

| Nr. | Titel | Geplant in |
|---|---|---|
| 0015 | Web-Stack-Entscheidung (FastAPI + Jinja2 vs. SPA) | M5 |
| 0016 | Read-Model-Strategie | M5 |
| 0017 | VPS-Deployment-Modell | M6 |
| 0018 | Backup/Restore-Strategie | M6 |
| 0019 | Update-Scout-Modell | M7 |
