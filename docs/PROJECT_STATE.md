# Project State

**Stand:** 2026-05-09
**Aktive Tranche:** M3 — Review & Publish (abgeschlossen, Push ausstehend)
**Aktuelle Version:** 0.4.0-wiki-review-publish (in Vorbereitung)
**Repository:** https://github.com/andreaskeis77/curio

Dieses Dokument ist die **lebende Statusübersicht** des Projekts. Es wird nach jeder relevanten Tranche aktualisiert.

---

## Was gerade gilt

- **Phase:** M3 abgeschlossen. Wiki-Pages mit 13 Seitentypen, Atomic Publish nach `wiki/`, Claim-Registry, Backlinks-Tabelle, Lint v0, optional Auto-Commit.
- **Was es schon gibt:** Repo, kanonische Dokumente, ADRs 0001–0013, ROADMAP, Konzepte, vollständige CLI mit `registry`, `capture`, `sources`, `extract`, `ingest`, `proposal` (list/show/approve/reject/request-changes), `quarantine`, `pages`, `lint`. SQLite v3 mit 15 Tabellen. LLM-Wrapper, Prompt-Registry, Quarantäne, Wiki-Pipeline mit Two-Phase-Publish, 13 Seitentyp-Templates, deterministischer Slug-Generator, atomic write, Git-Helper.
- **Was es noch nicht gibt:** Sucharchitektur (FTS5), Browse-CLI, Backlinks-Auto-Computation, Web-UI, VPS-Deployment, Update Scouts.
- **LLM-Modus:** Mock-Default. Anthropic/OpenAI implementiert.
- **Pilotbereiche im Fokus:** UNESCO und Pacojet (Fixtures vorhanden, Pipeline vollständig nutzbar).

## Letzte abgeschlossene Tranche

**M3 — Review & Publish**

Deliverables:

- **ADR-0012** Atomic Writes und Git-Commit-Strategie (Two-Phase Publish, Default kein Auto-Commit).
- **ADR-0013** Claim-Provenienz-Modell (harte Fakten mit Source-Bindung).
- **SQLite-Schema v3** (Migration 0003): `pages`, `page_sources`, `claims`, `links`, `lint_runs`, `lint_findings` mit Foreign Keys.
- **Wiki-Domain-Modell**: `Page`, `Claim`, `PageType` (13 Typen), `PageStatus`, `Freshness`, `ConfidenceLevel`, `SourceRelation`.
- **Slugify**: deterministisch mit deutschen Umlauten (ae/oe/ue/ss), französischen Akzenten, max-length, Disambiguierung mit `-2`/`-3`.
- **Frontmatter**: Render/Parse/Validate mit YAML, Pflichtfeld-Check, Enum-Check, ID-Präfix-Check.
- **Templates** für 12 Seitentypen mit standard-Sektionen pro Typ (Topic, Place, Person, Recipe, Method, Experiment, Product Research, Event, Collection, Question, Work, Brand) plus Source-Page-Renderer.
- **Atomic Write**: temp file → fsync → atomic rename mit best-effort cleanup.
- **Git-Helper**: `git status`, `git add`, `git commit`, `auto_commit_publish` mit Pre-Check für saubere working tree.
- **Page/Claim/Link/PageSource Repositories** mit Standard-CRUD und Lookups.
- **Publish-Pipeline** (`publish_proposal`): Two-Phase, Slug-Kollision-Check in Phase A, atomic writes in Phase B, Source-Page-Generierung (idempotent), Claim-Marker im Markdown-Body, optional Auto-Commit.
- **Reject** und **Request-Changes** mit Status-Update und optional `review_notes.md`.
- **Lint v0** mit 10+ Regeln: frontmatter_invalid, slug_mismatch, claim_missing_source, page_without_sources, broken_wikilink, duplicate_title, product_without_review_after, review_after_overdue, page_too_long, stale_extracted_path, volatile_without_review_after.
- **Lint-Persistenz** in `lint_runs`/`lint_findings` mit FK-Sicherheit (nur bekannte Page-/Source-IDs).
- **Lint-Markdown-Report** in `docs/_ops/lint_reports/<run_id>.md`.
- **CLI**: `proposal approve/reject/request-changes`, `pages list`, `lint --report`. Approve: exit 1 bei Publish-Error, exit 2 bei Slug-Kollision.
- **Tests**: 38 neue (slugify, frontmatter, publish, lint, cli-m3). Gesamttests: **181 grün**.

Akzeptanzkriterien M3 (alle erfüllt):

- Proposal kann angenommen, verworfen, geändert werden.
- Annahme erzeugt saubere Markdown-Seiten mit gültigem Frontmatter (validiert in Tests).
- `wiki/sources/<slug>.md` und `wiki/<type>/<slug>.md` werden atomic geschrieben.
- Source-Page wird idempotent erzeugt.
- Slug-Kollision wird in Phase A erkannt, kein Schreibvorgang.
- Reject und Request-Changes erzeugen **keine** Wiki-Dateien (Test verifiziert).
- Claim-Registry: harte Fakten aus Proposal werden persistiert (Fixture-Test).
- Lint findet absichtlich eingebaute Fehler.
- Auto-Commit ist Default-OFF.
- 4/4 Quality Gates grün.

## Aktive Tranche

Keine. Nächste: **M4 — Browse, Search, Lint**.

## Offene rote Pfade

Keine.

## Bekannte Einschränkungen

- Heuristische Hard-Fact-Erkennung ist regex-basiert — Wikilink-Inhalte mit Jahreszahl können false positives erzeugen.
- Backlinks-Tabelle (`links`) existiert, wird aber noch nicht aktiv beim Publish gefüllt — kommt in M4.
- Slug-Kollision blockt Publish; M3 hat noch keinen "update existing page"-Pfad.
- Mock-Provider liefert default-output ohne `hard_facts`; für Publish-Tests mit Claims muss manuell eine Fixture angelegt werden.

## Aktuelle Umgebung

| Komponente | Stand |
|---|---|
| Python | 3.11+ (getestet auf 3.12) |
| Lint | ruff 0.5+ — alles grün |
| Test | pytest 8.0+ — 181 Tests grün |
| Plattform | Windows 11 Pro (Dev), später Windows VPS |
| LLM Provider | mock (Default) / anthropic / openai |
| Registry | SQLite v3 (15 Tabellen) |
| Web UI | nicht vorhanden (kommt in M5) |
| Dependencies | trafilatura 2.0, pypdf 6.10, pydantic 2.13, click, rich, pyyaml |

## Nächste Tranche: M4 — Browse, Search, Lint

Geplante Deliverables:

- SQLite FTS5 Index über Wiki-Seiten.
- CLI: `search "<query>"`, `browse --random`, `browse --topic <name>`, `browse --collection <name>`.
- Mehr Lint-Regeln (Ziel: 12+).
- Backlinks-Auto-Computation beim Publish.
- Open-Questions-Aggregation.
- Freshness-Dashboard-Daten.
- Golden Questions: `eval/golden-questions.yaml`.
- `eval golden` CLI.
- Index-Rebuild aus Wiki-Markdown.
- ADR-0014: Sucharchitektur (Stufenmodell-Implementierung).

## Zuletzt aktualisiert

- 2026-05-08 — initial (T0.1 abgeschlossen).
- 2026-05-08 — M1 Registry Spine abgeschlossen.
- 2026-05-09 — M2 Extraction & Proposal Ingest abgeschlossen.
- 2026-05-09 — M3 Review & Publish abgeschlossen.

## Wie dieses Dokument zu pflegen ist

Nach jeder abgeschlossenen Tranche: „Letzte abgeschlossene Tranche" aktualisieren, „Aktive Tranche" auf nächste Phase setzen, Quality Gates verifizieren, ARD/ADR/RUNBOOK bei Architekturwirkung aktualisieren, Datum erweitern.
