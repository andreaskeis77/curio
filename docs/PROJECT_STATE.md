# Project State

**Stand:** 2026-05-09
**Aktive Tranche:** M4 — Browse, Search, Lint (abgeschlossen, Push ausstehend)
**Aktuelle Version:** 0.5.0-search-and-browse (in Vorbereitung)
**Repository:** https://github.com/andreaskeis77/curio

Dieses Dokument ist die **lebende Statusübersicht** des Projekts. Es wird nach jeder relevanten Tranche aktualisiert.

---

## Was gerade gilt

- **Phase:** M4 abgeschlossen. FTS5-Volltextsuche, Browse-Lesepfade (random/topic/collection), Backlinks-Auto-Compute beim Publish, Lint mit 13 Regeln, Open-Questions-Aggregation, Freshness-Dashboard, Golden-Questions-Eval-Runner.
- **Was es schon gibt:** Repo, kanonische Dokumente, ADRs 0001–0014, ROADMAP, Konzepte, vollständige CLI mit `registry`, `capture`, `sources`, `extract`, `ingest`, `proposal` (list/show/approve/reject/request-changes), `quarantine`, `pages`, `lint`, `search`, `index rebuild`, `browse`, `questions list`, `freshness`, `eval golden`. SQLite v4 mit 16 Tabellen (15 + `pages_fts` virtuelle Tabelle). LLM-Wrapper, Prompt-Registry, Quarantäne, Wiki-Pipeline mit Two-Phase-Publish, 13 Seitentyp-Templates, deterministischer Slug-Generator, atomic write, Git-Helper, Backlinks, FTS-Index.
- **Was es noch nicht gibt:** Web-UI, VPS-Deployment, Update Scouts, Embeddings/Hybrid Retrieval.
- **LLM-Modus:** Mock-Default. Anthropic/OpenAI implementiert.
- **Pilotbereiche im Fokus:** UNESCO und Pacojet (Fixtures vorhanden, Pipeline vollständig nutzbar bis Suche).

## Letzte abgeschlossene Tranche

**M4 — Browse, Search, Lint**

Deliverables:

- **ADR-0014** Sucharchitektur Stufe 1 — FTS5-Implementierung. Eigenständige `pages_fts`-Tabelle, Filter per Join auf `pages`, Rebuild aus Wiki-Markdown, `unicode61`-Tokenizer mit `remove_diacritics`.
- **Schema-Migration v4**: virtuelle FTS5-Tabelle `pages_fts(page_id UNINDEXED, title, body, tags, why_interesting)`.
- **Backlinks-Auto-Compute beim Publish**: Wikilinks aus Body extrahieren, gegen `pages.title` resolven, sonst `status='broken'`. Idempotent via `LinkRepository.delete_for_page`.
- **`PageRepository.find_by_title`** (case-insensitive).
- **Lint-Bugfix**: Hard-Fact-Heuristik strippt `[[...]]` vor Pattern-Match — `[[Pacojet 1984]]` ist kein false-positive year-Fakt mehr.
- **Lint-Erweiterung**: `orphan_page` (info; Source/Question/Collection ausgenommen), `alias_collision` (warning). **Lint hat jetzt 13 Regeln** (Ziel 12+ erreicht).
- **`search/`-Modul**: `index_page`, `delete_page`, `rebuild_index_from_markdown`, `search_pages` mit Filter-Validierung gegen Enums (type/freshness/status/tag), bm25-Ranking, snippet-Extraktion.
- **Publish-FTS-Hook**: in Phase B nach Page-Insert wird `pages_fts` befüllt (lazy import wegen Zirkel).
- **`browse/`-Modul**: `browse_random` (excl. Source-Pages), `browse_by_topic` (via Topic-Page-Backlinks, LIKE-Fallback), `browse_by_collection` (via outgoing Wikilinks).
- **`wiki/aggregations.py`**: `collect_open_questions` (Question-Pages + Frontmatter `open_questions:`), `collect_freshness_status` (overdue / due_within_7_days / volatile_without_schedule).
- **`evals/golden.py`**: Goldenrunner für `eval/golden-questions.yaml` mit Question-Types `search`, `browse_random`, `browse_topic`, `browse_collection`, `open_questions`, `freshness`, `index_rebuild`. Unterstützt `expect_error` für kontrollierte Negativ-Tests.
- **`eval/golden-questions.yaml`**: 10 strukturelle Smoke-Goldens, die auf jedem Wiki-Stand laufen.
- **CLI**: `search "<query>"` mit Filtern, `index rebuild`, `browse --random|--topic|--collection`, `questions list`, `freshness`, `eval golden` mit Markdown-Report.
- **E2E-Smoke-Test** in `tests/test_smoke.py`: capture → extract → ingest → approve → search findet die Mock-Page.
- **Tests**: 25 neue (test_links 3, test_lint +4, test_search 8, test_browse 5, test_aggregations 3, test_eval_golden 2, test_smoke +1). **Gesamttests: 207 grün**.

Akzeptanzkriterien M4 (alle erfüllt):

- Suche findet Pages nach Titel und Volltext.
- Browse erzeugt sinnvolle Lesepfade (random / topic / collection).
- Lint findet absichtlich eingebaute Fehler aus 13 Regeln (Ziel 12+).
- Backlinks werden bei Publish gefüllt.
- Index ist rebuildbar (`curiosity index rebuild`).
- Golden Questions laufen und prüfen Erwartungen — 10/10 PASS.
- 4/4 Quality Gates grün.

## Aktive Tranche

Keine. Nächste: **M5 — Local Web UI**.

## Offene rote Pfade

Keine.

## Bekannte Einschränkungen

- Heuristische Hard-Fact-Erkennung ist regex-basiert — Wikilink-Inhalte mit Jahreszahl sind seit M4 nicht mehr false-positiv, andere Patterns können es weiterhin sein.
- `pages_fts` muss nach manuellen Markdown-Edits per `curiosity index rebuild` re-syncen, sonst veraltet die Suche.
- Slug-Kollision blockt Publish; ein "update existing page"-Pfad fehlt weiterhin.
- Mock-Provider liefert default-output ohne `hard_facts`; für Publish-Tests mit Claims muss manuell eine Fixture angelegt werden.
- Goldens sind aktuell strukturelle Smoke-Tests; inhaltliche Goldens kommen mit Pilot-Content (frühestens M5).

## Aktuelle Umgebung

| Komponente | Stand |
|---|---|
| Python | 3.11+ (getestet auf 3.12) |
| Lint | ruff 0.5+ — alles grün |
| Test | pytest 8.0+ — 207 Tests grün |
| Plattform | Windows 11 Pro (Dev), später Windows VPS |
| LLM Provider | mock (Default) / anthropic / openai |
| Registry | SQLite v4 (15 Tabellen + `pages_fts` virtuelle FTS5-Tabelle) |
| Web UI | nicht vorhanden (kommt in M5) |
| Dependencies | trafilatura 2.0, pypdf 6.10, pydantic 2.13, click, rich, pyyaml |

## Nächste Tranche: M5 — Local Web UI

Geplante Deliverables (siehe ROADMAP §M5):

- FastAPI-Backend (`/api/health`, `/api/pages`, `/api/sources`, `/api/search`, `/api/browse/random-walk`, `/api/lint/report/latest`).
- Read-Models (`site_index.json`, `graph.json`, `search_documents.jsonl`, `freshness_dashboard.json`, `page_cards.json`, `mobile_nav.json`).
- Server-rendered HTML (Jinja2), optional htmx.
- Home-Dashboard (Weiterlesen, Heute interessant, Offene Fragen, Needs Review, Veraltet, Random Walk).
- Page-Reader mit Source-Drawer, Backlinks, Freshness-/Confidence-Badges.
- Mobile-First-Layout.
- ADR-0015 Web-Stack-Entscheidung, ADR-0016 Read-Model-Strategie.

## Zuletzt aktualisiert

- 2026-05-08 — initial (T0.1 abgeschlossen).
- 2026-05-08 — M1 Registry Spine abgeschlossen.
- 2026-05-09 — M2 Extraction & Proposal Ingest abgeschlossen.
- 2026-05-09 — M3 Review & Publish abgeschlossen.
- 2026-05-09 — M4 Browse, Search, Lint abgeschlossen.

## Wie dieses Dokument zu pflegen ist

Nach jeder abgeschlossenen Tranche: „Letzte abgeschlossene Tranche" aktualisieren, „Aktive Tranche" auf nächste Phase setzen, Quality Gates verifizieren, ARD/ADR/RUNBOOK bei Architekturwirkung aktualisieren, Datum erweitern.
