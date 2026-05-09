# Project State

**Stand:** 2026-05-09
**Aktive Tranche:** M5 — Local Web UI (abgeschlossen, Push ausstehend)
**Aktuelle Version:** 0.6.0-local-web-ui (in Vorbereitung)
**Repository:** https://github.com/andreaskeis77/curio

Dieses Dokument ist die **lebende Statusübersicht** des Projekts. Es wird nach jeder relevanten Tranche aktualisiert.

---

## Was gerade gilt

- **Phase:** M5 abgeschlossen. Lokal startbare Web-UI auf FastAPI + Jinja2, Read-Models als JSON/JSONL, JSON-API für alle Curiosity-Domänen, Mobile-First-CSS.
- **Was es schon gibt:** Repo, kanonische Dokumente, ADRs 0001–0016, ROADMAP, Konzepte, vollständige CLI mit `registry`, `capture`, `sources`, `extract`, `ingest`, `proposal`, `quarantine`, `pages`, `lint`, `search`, `index rebuild`, `browse`, `questions list`, `freshness`, `eval golden`, `readmodels rebuild|status`, `web run`. SQLite v4 mit 16 Tabellen (15 + `pages_fts`). Read-Models in `read_models/`. FastAPI-Backend mit allen geplanten Endpunkten. Jinja2-Templates für Home, Page-Reader, Search, Source mit handgeschriebenem Mobile-First-CSS.
- **Was es noch nicht gibt:** VPS-Deployment, Backup/Restore, Update Scouts, Embeddings/Hybrid Retrieval.
- **LLM-Modus:** Mock-Default. Anthropic/OpenAI implementiert.
- **Pilotbereiche im Fokus:** UNESCO und Pacojet (Fixtures vorhanden, Pipeline vollständig nutzbar bis Web-Reader).

## Letzte abgeschlossene Tranche

**M5 — Local Web UI**

Deliverables:

- **ADR-0015** Web-Stack — FastAPI + Jinja2. Begründet die Entscheidung gegen SPA und statische Generierung. Definiert das Verzeichnis-Layout `web/api/`, `web/views/`, `web/templates/`, `web/static/`.
- **ADR-0016** Read-Model-Builder-Strategie. Voller Rebuild, expliziter CLI-Trigger, `meta.schema_version` pro Read-Model, atomic write per File.
- **`read_models/`-Modul**: `build_site_index`, `build_graph`, `build_search_documents` (JSONL), `build_freshness_dashboard`, `build_page_cards` (mit Backlink-Count), `build_mobile_nav`, `build_open_questions`. `rebuild_all` ist atomic per File. `read_model_status` liest `meta`-Block für Build-Status.
- **CLI** `curiosity readmodels rebuild|status` und `curiosity web run --host/--port/--reload`.
- **FastAPI JSON-API** unter `/api/`: `health` (mit Read-Model-Status), `pages` (list + detail mit Body und Backlinks), `sources`, `search` (FTS5-Filter mit Validierung), `browse/random-walk|topic|collection`, `proposals` (read-only), `lint/report/latest`. OpenAPI-Doku unter `/docs`.
- **Per-Request-Connection** via FastAPI-Dependency `get_conn`, FK-Enforcement an.
- **HTML-Views** unter `/`, `/p/<slug>`, `/search`, `/s/<source_id>`, plus `/healthz`-Liveness. Wikilink-Resolver pre-processed `[[Title]]` zu `/p/<slug>`-Anchors oder `span.broken-link`.
- **Markdown-Rendering** über `markdown-it-py` (commonmark + linkify + table).
- **Mobile-First-CSS** (handgeschrieben) mit Custom-Properties, Dark-Default + `prefers-color-scheme: light`, Type-/Freshness-/Confidence-Badges, Card-Grid (1/2/3 Spalten), Source-Drawer als `<details>`, `prefers-reduced-motion`-Respektierung.
- **Accessibility-Basics**: skip-link, semantic HTML, Landmarks (`role="banner"`, `role="main"`, `role="contentinfo"`), Tastatur-Navigation, focus-visible-Default.
- **Dependencies**: `fastapi`, `jinja2`, `uvicorn`, `markdown-it-py` als runtime-deps; `httpx` als dev-dep. Ruff per-file-ignore B008 für `web/**` (FastAPI-Pattern).
- **Tests (42 neu, total 249)**: `test_read_models.py` (10), `test_api.py` (20), `test_views.py` (12). Alle JSON-Endpunkte plus 4xx-Pfade, Wikilink-Resolution, Backlinks-Roundtrip, Static-CSS, end-to-end Capture-to-Search-via-API.

Akzeptanzkriterien M5 (Status):

- Home lädt lokal auf 127.0.0.1 — bestätigt durch TestClient (`/`, `/healthz`, `/api/health`). Browser-Smoke offen für Andreas.
- UNESCO/Pacojet-Beispielseiten lesbar — Pipeline ist getestet, Pilot-Content kann publiziert werden.
- **Mobile Smoke per Browser DevTools** — von Andreas zu bestätigen (nicht durch Tests abgedeckt).
- UI liest aus Read Models und Wiki, nicht direkt aus Raw — Read-Models gebaut, FastAPI nutzt sie via Health.
- Suche und Browse funktionieren — getestet via `/api/search`, `/api/browse/*`, `/search`-View.
- `/api/health` ist grün — getestet.
- Quellen, Freshness, Confidence sichtbar — Page-Reader und Home zeigen die Badges.

## Aktive Tranche

Keine. Nächste: **M6 — VPS Read-only Preview**.

## Offene rote Pfade

Keine.

## Bekannte Einschränkungen

- Mobile-Smoke per Browser-DevTools wurde nicht automatisiert getestet — Andreas muss `curiosity web run` lokal starten und auf Mobile-Layout prüfen.
- Read-Models werden **nicht** automatisch beim Publish neu gebaut — nach mehreren Approves manuell `curiosity readmodels rebuild` aufrufen, sonst zeigt die UI veralteten Stand.
- `pages_fts` muss nach manuellen Markdown-Edits per `curiosity index rebuild` re-syncen.
- Slug-Kollision blockt Publish; ein "update existing page"-Pfad fehlt weiterhin.
- Heuristische Hard-Fact-Erkennung ist regex-basiert.
- Mock-Provider liefert default-output ohne `hard_facts`; für Publish-Tests mit Claims wird manuell eine Fixture angelegt.

## Aktuelle Umgebung

| Komponente | Stand |
|---|---|
| Python | 3.11+ (getestet auf 3.12) |
| Lint | ruff 0.5+ — alles grün |
| Test | pytest 8.0+ — 249 Tests grün |
| Plattform | Windows 11 Pro (Dev), später Windows VPS |
| LLM Provider | mock (Default) / anthropic / openai |
| Registry | SQLite v4 (15 Tabellen + `pages_fts` virtuelle FTS5-Tabelle) |
| Web UI | FastAPI + Jinja2 + Mobile-First-CSS, lokal über `curiosity web run` |
| Dependencies | fastapi 0.115+, jinja2 3.1+, uvicorn 0.30+, markdown-it-py 3.0+, plus die bestehenden |

## Nächste Tranche: M6 — VPS Read-only Preview

Geplante Deliverables (siehe ROADMAP §M6):

- Publish-Bundle-Builder (filtert private Raw Sources).
- Deployment-Skript `scripts/deploy-windows-vps.ps1`.
- Windows-Service-Konfiguration (WinSW oder NSSM).
- Reverse Proxy: Caddy oder Cloudflare Tunnel.
- Tailscale für Admin-Zugang.
- Backup-/Restore-Skripte und -Drill.
- Health-Endpoints `/healthz` (vorhanden), `/healthz/deep` (neu).
- ADR-0017 VPS-Deployment-Modell, ADR-0018 Backup/Restore-Strategie.

## Zuletzt aktualisiert

- 2026-05-08 — initial (T0.1 abgeschlossen).
- 2026-05-08 — M1 Registry Spine abgeschlossen.
- 2026-05-09 — M2 Extraction & Proposal Ingest abgeschlossen.
- 2026-05-09 — M3 Review & Publish abgeschlossen.
- 2026-05-09 — M4 Browse, Search, Lint abgeschlossen.
- 2026-05-09 — M5 Local Web UI abgeschlossen.

## Wie dieses Dokument zu pflegen ist

Nach jeder abgeschlossenen Tranche: „Letzte abgeschlossene Tranche" aktualisieren, „Aktive Tranche" auf nächste Phase setzen, Quality Gates verifizieren, ARD/ADR/RUNBOOK bei Architekturwirkung aktualisieren, Datum erweitern.
