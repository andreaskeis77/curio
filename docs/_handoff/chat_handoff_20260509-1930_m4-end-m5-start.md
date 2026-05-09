# Chat Handoff — M4 Ende / M5 Start (Local Web UI)

**Erstellt:** 2026-05-09
**Letzte abgeschlossene Tranche:** M4 — Browse, Search, Lint (`v0.5.0-search-and-browse`, Tag in Vorbereitung)
**Nächste Tranche:** M5 — Local Web UI
**Repo:** https://github.com/andreaskeis77/curio

---

## Zustand am Ende dieser Session

- 207 pytest-Tests grün, alle 4 Quality Gates grün (pytest, ruff check, ruff format, secret-scan).
- Working Tree sauber bis auf den letzten M4d-Commit (PROJECT_STATE / ROADMAP / Handoff / CLI-Help).
- Schema v4 mit 15 Tabellen + `pages_fts` virtueller FTS5-Tabelle.
- ADRs 0001–0014. ADR-0014 dokumentiert die Sucharchitektur Stufe 1.
- CLI hat: `registry`, `capture`, `sources`, `extract`, `ingest`, `proposal`, `quarantine`, `pages`, `lint`, `search`, `index rebuild`, `browse`, `questions list`, `freshness`, `eval golden`, plus `info`, `paths`, `quality-gates`.
- Mock-LLM-Default weiterhin verbindlich — Anthropic/OpenAI implementiert, aber nicht in der Test-Suite.

## Was nicht im PROJECT_STATE steht (Notizen für die nächste Session)

### 1. Lazy-Import in `wiki/publish.py` für `search.index`

Beim Implementieren von M4b ergab sich ein zirkulärer Import: `search.index → wiki.frontmatter` triggert die Initialisierung von `wiki/__init__.py`, was `wiki.publish → search.index` zurückimportiert. Lösung: in `publish_proposal` wird `from curiosity_wiki.search.index import index_page` lazy aufgerufen. Wenn M5 das Web-API hinzufügt und ähnliche Topologie-Cycles entstehen, dasselbe Pattern nutzen — oder das `wiki/__init__.py`-Re-Export schlanker machen.

### 2. FTS-Konsistenz bei manuellen Edits

`pages_fts` wird beim Publish gefüllt. Wer manuell ein Markdown-File ändert, hat ein veraltetes FTS, bis `curiosity index rebuild` läuft. Für M5 wichtig: bei jedem Smoke-Run (z.B. CI) `index rebuild` mit aufnehmen, oder Read-Models aus `pages` + Markdown-Files konsequent neu ableiten.

### 3. Browse-Topic-Fallback

`browse_by_topic` sucht zuerst nach einer Topic-Page mit dem Title; wenn keine existiert, fällt es auf `LIKE %topic%`-Match auf Page-Titel zurück. Das ist gewollt (Browse soll auf leerem Wiki sinnvoll bleiben), aber die Web-UI sollte explizit anzeigen, wenn der Fallback greift, damit User wissen, dass Topic noch keine Hub-Page hat.

### 4. Goldens sind strukturell

`eval/golden-questions.yaml` enthält 10 Smoke-Goldens. Inhaltliche Goldens (UNESCO/Pacojet-Content) kommen, sobald Pilot-Pages publiziert sind. Die Format-Definition (id, type, expectations, expect_error) ist stabil und für Inhalts-Goldens erweiterbar.

### 5. Backlinks sind nun in der DB

`links` wird beim Publish gefüllt. Lint-Regel `broken_wikilink` läuft trotzdem weiterhin per File-Scan — das ist robuster, weil es Markdown direkt prüft. Wenn M5 eine "Backlinks anzeigen"-UI baut, kann sie `LinkRepository.backlinks(page_id)` nutzen und den File-Scan verlassen.

### 6. Auto-Commit Default

`CURIOSITY_PUBLISH_AUTO_COMMIT=false` bleibt Default, auch in M4. M5 sollte daran nichts ändern — die Web-UI ist read-only im MVP, wie im ROADMAP geplant.

### 7. CLI-Help-String pflegen

`@click.group(help=...)` und `info`-Phasen-Footer wurden in M4d auf "M4" umgestellt. Bei M5 entsprechend anpassen.

## M5 Scope (aus ROADMAP.md)

**Ziel:** Lesen und Schmökern funktionieren am Laptop und Smartphone.

### Deliverables

- FastAPI-Backend mit Endpunkten: `/api/health`, `/api/pages`, `/api/pages/{id}`, `/api/sources`, `/api/search`, `/api/browse/random-walk`, `/api/proposals` (read-only im MVP), `/api/lint/report/latest`.
- Read-Models: `read_models/site_index.json`, `graph.json`, `search_documents.jsonl`, `freshness_dashboard.json`, `page_cards.json`, `mobile_nav.json`.
- Server-rendered HTML mit Jinja2 (kein SPA im MVP).
- Optional htmx für kleine Interaktionen.
- Home Dashboard: Weiterlesen, Heute interessant, Offene Fragen, Needs Review, Veraltet, Random Walk.
- Page Reader mit Source-Drawer, Backlinks, Freshness-Badges, Confidence-Badge.
- Mobile-First Layout (< 768px), Tablet (768–1024px), Desktop (> 1024px).
- Search-Page (FTS-Backend ist da).
- Source-Page mit Raw-Snapshot-Link.
- Accessibility-Basics: semantic HTML, Tastaturnavigation, Kontrast, `prefers-reduced-motion`.
- ADR-0015: Web-Stack-Entscheidung (FastAPI + Jinja2 vs. SPA).
- ADR-0016: Read-Model-Strategie.

### Akzeptanzkriterien

- Home lädt lokal auf 127.0.0.1.
- UNESCO- und Pacojet-Beispielseiten lesbar.
- Mobile Smoke per Browser DevTools grün.
- UI liest aus Read Models und Wiki, nicht direkt aus Raw.
- Suche und Browse funktionieren.
- `/api/health` ist grün.
- Quellen, Freshness, Confidence sichtbar.

### Bewusst nicht in M5

- VPS-Deployment (M6).
- Schreibfunktionen in der UI (später).
- PWA / Offline-Modus (Phase F).

## Tipps für die Umsetzung

1. **Read-Models** sind rebuildbare JSON-Files. Generator-Modul `read_models/builder.py` mit pro-Read-Model-Funktionen (`build_site_index`, `build_graph`, `build_search_documents`, ...). Neuer CLI-Command `curiosity readmodels rebuild`.

2. **FastAPI** lädt Read Models beim Start in einen In-Memory-Cache. Auf `--reload` im Dev-Modus reagieren. Endpunkte sind dünne Adapter — Search nutzt die bereits implementierten `search_pages`/`browse_*`-Funktionen.

3. **Templates** trennen Layout (`base.html`), Page-Reader (`page.html`), Source-Drawer (`partials/source_drawer.html`), Cards (`partials/page_card.html`). Mobile-first per CSS-Custom-Properties + `clamp()`.

4. **Tests-Konvention** wie M4: pro Domain ein Test-File (`test_readmodels.py`, `test_api.py`, `test_views.py`). Für API-Tests `httpx.AsyncClient` oder `TestClient`.

5. **Smoke-Test M5**: Server starten → `/api/health` 200 → `/api/pages` liefert Liste → `/` rendert HTML mit "Heute interessant"-Sektion.

## Nicht-vergessen-Liste

- [ ] ADR-0009 README-Eintrag für ADR-0015/0016 ergänzen (wenn entschieden).
- [ ] PROJECT_STATE.md auf M5-Scope aktualisieren wenn fertig.
- [ ] Quality Gates komplett grün (pytest, ruff, format, secret-scan).
- [ ] Smoke: `uvicorn ...` Server hochfahren, `curl /api/health` 200.
- [ ] Mobile-Smoke per Browser-DevTools (>= 320px).
- [ ] Tag `v0.6.0-local-web-ui` (nach ROADMAP-Konvention).
- [ ] Diesen Handoff bei Bedarf als „abgeschlossen" markieren.

## Quick-Recovery für Cold Start

```powershell
cd c:\projekte\curio
.\.venv\Scripts\Activate.ps1
python -m curiosity_wiki info        # zeigt Phase, Schema-Version, Source-Count
python -m pytest -q                  # erwartet: 207 passed
python tools\run_quality_gates.py    # erwartet: 4/4 OK
git log --oneline -5                 # erwartet: M4d-Commit zuoberst
git tag                              # erwartet: v0.5.0-search-and-browse
python -m curiosity_wiki eval golden # erwartet: 10/10 PASS
```

Falls etwas anders: PROJECT_STATE.md prüfen, dort steht der wahre Stand.
