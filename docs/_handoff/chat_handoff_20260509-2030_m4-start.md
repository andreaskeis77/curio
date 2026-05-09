# Chat Handoff — M4 Start (Browse / Search / Lint-Erweiterung)

**Erstellt:** 2026-05-09
**Letzte abgeschlossene Tranche:** M3 — Review & Publish (`v0.4.0-wiki-review-publish`, Commit `99c4be4`)
**Nächste Tranche:** M4 — Browse, Search, Lint
**Repo:** https://github.com/andreaskeis77/curio

---

## Zustand am Ende der vorigen Session

- 181 pytest-Tests grün, alle 4 Quality Gates grün (pytest, ruff check, ruff format, secret-scan).
- Working Tree sauber, alle Commits gepusht, 4 Tags auf GitHub.
- Schema v3 mit 15 Tabellen, inkl. `links`, `lint_runs`, `lint_findings` (in M3 angelegt aber noch nicht voll genutzt).
- CLI hat: `registry`, `capture`, `sources`, `extract`, `ingest`, `proposal`, `quarantine`, `pages`, `lint`, `info`, `paths`, `quality-gates`.
- Mock-LLM-Default funktioniert; Anthropic/OpenAI implementiert, aber nicht in Tests.

## Was nicht im PROJECT_STATE steht (Notizen für die nächste Session)

### 1. Backlinks-Tabelle existiert, ist leer

In M3 wurde die `links`-Tabelle angelegt, aber `publish_proposal` füllt sie noch nicht. Bei M4-Backlinks-Auto-Compute:

- Beim Publish: alle `[[Title]]`-Pattern im Body extrahieren und in `links` schreiben.
- `LinkRepository.insert(from_page_id, to_page_id, target_text, status)` ist da.
- Bei unbekanntem Target: `to_page_id=None`, `status='broken'` — sind dann auch via `links` queryable für Lint.
- Beim erneuten Publish einer Page: vorher `LinkRepository.delete_for_page(page_id)`.

### 2. Lint hat schon `broken_wikilink`-Regel, aber per File-Scan, nicht per Registry

Wenn M4 Backlinks-Auto-Compute hinzufügt, könnte die `broken_wikilink`-Lint-Regel statt File-Scan einfach `LinkRepository.broken_links()` nutzen. Dann ist sie konsistent mit der Registry und schneller.

### 3. Heuristische Hard-Fact-Erkennung false positive

Im Smoke-Test wurde ein Wikilink `[[Pacojet 1984]]` als hard fact (year) erkannt, weil das Datum im Wikilink-Text steht. Das ist false positive. M4 sollte:

- Wikilinks (`[[...]]`) aus dem Body strippen, bevor die Hard-Fact-Heuristik läuft, oder
- Die Heuristik so anpassen, dass Zeilen mit `[[` ignoriert werden, wenn das Pattern im Wikilink-Text liegt.

### 4. Mock-Provider-Fixture-Pfad

`tests/fixtures/llm_outputs/ingest_v0_1/<source_id>.yaml` wird vom Mock-Provider geladen. Aber:

- Der Pfad wird via `get_vault_root()` aufgelöst — funktioniert nur, wenn `CURIOSITY_VAULT_ROOT` gesetzt ist.
- In `tests/test_wiki_publish.py::test_publish_creates_claim_when_hard_facts_present` wird das via `monkeypatch.setenv` gemacht.
- Wenn M4 Tests mit spezifischen LLM-Outputs braucht, dieses Pattern wiederverwenden.

### 5. SQLite FTS5 — Verfügbarkeit prüfen

Python 3.12 mit Standard-SQLite hat FTS5 fast immer dabei, aber nicht garantiert. Erster M4-Schritt:

```python
sqlite3.connect(":memory:").execute("CREATE VIRTUAL TABLE t USING fts5(x)")
```

Wenn das fehlschlägt: Fallback auf BM25-Eigen-Implementation oder Rebuild ohne FTS.

### 6. Page-Update-Pfad fehlt

M3 hat keinen "Page wurde schon publiziert, jetzt mit neuem Proposal updaten"-Pfad. Aktuell wirft es `SlugCollisionError`. Für M4 ist das nicht prioritär — kommt eher in einer eigenen späteren Tranche oder wenn der Bedarf konkret entsteht.

### 7. Auto-Commit Default

`CURIOSITY_PUBLISH_AUTO_COMMIT=false` ist Default. Das bleibt so. Andreas kann es in `.env` aktivieren, wenn er es will. Tests setzen `auto_commit=False` explizit.

## M4 Scope (aus ROADMAP.md)

**Ziel:** Wiki ist nutzbar, durchsuchbar, pflegbar.

### Deliverables

- SQLite FTS5 Index über Wiki-Seiten (über `pages.title` + Body).
- CLI: `search "<query>"` mit Filter nach Typ/Status/Freshness/Tag.
- CLI: `browse --random`, `browse --topic <name>`, `browse --collection <name>`.
- Lint-Regeln erweitern (Ziel: 12+, aktuell 11). Mögliche neue:
  - `orphan_page` (Page ohne Backlinks und nicht in collections referenziert)
  - `proposal_without_diff` (für update-proposals — nicht in M4 dringend)
  - `untranslated_alias_collision` (Alias clash mit anderem Page-Title)
- Backlinks-Auto-Computation beim Publish (`links`-Tabelle füllen).
- Open-Questions-Aggregation: alle `question`-Pages und alle `open_questions:`-Frontmatter-Felder zusammenfassen.
- Freshness-Dashboard-Daten: Pages mit überschrittenem `review_after`.
- Golden Questions in `eval/golden-questions.yaml`.
- CLI: `eval golden` läuft Fragen gegen Wiki, prüft Output-Struktur.
- Index-Rebuild aus Wiki-Markdown (`curiosity index rebuild`).
- ADR-0014 Sucharchitektur-Implementierung (Stage 1 FTS5, mit Pfad zu Stage 2 Embeddings).

### Akzeptanzkriterien

- Suche findet Pages nach Titel und Volltext.
- Browse erzeugt sinnvolle Lesepfade.
- Lint findet absichtlich eingebaute Fehler aus mindestens 12 Regeln.
- Golden Questions laufen und prüfen Erwartungen.
- Index ist rebuildbar (`curiosity index rebuild`).
- Backlinks werden bei Publish gefüllt.

### Bewusst nicht in M4

- Embeddings (Phase E).
- Web-UI (M5).
- Hybrid Retrieval (Phase E).

## Tipps für die Umsetzung

1. **FTS5 als virtuelle Tabelle** mit `content=pages` und Triggers, oder einfache eigene `pages_fts`-Tabelle, die beim Publish/Rebuild mitgeschrieben wird. Letzteres ist robuster.

2. **Backlinks-Auto-Compute beim Publish** ist ein kleiner Eingriff in `wiki/publish.py`:
   - Nach dem Frontmatter-Schreiben: Wikilinks aus Body extrahieren.
   - `LinkRepository.delete_for_page(page_id)` (für Re-Publish-Idempotenz).
   - Pro Wikilink: Page-Title in `pages` lookupen → wenn gefunden, `to_page_id` setzen, sonst `status='broken'`.

3. **Index-Rebuild** sollte alle `pages` und `wiki/`-Files zusammenführen — aktuell sind sie konsistent, aber wenn jemand manuell editiert, muss `rebuild` das wieder syncen. CLI: `curiosity index rebuild` oder `curiosity registry rebuild-from-markdown`.

4. **Golden Questions-Format** liegt schon in [docs/EVAL_STRATEGY.md](../EVAL_STRATEGY.md) skizziert — daran orientieren.

5. **Tests-Konvention** wie M3: pro Domain ein Test-File (`test_search.py`, `test_browse.py`, `test_eval_golden.py`, `test_links.py`, `test_cli_m4.py`).

## Nicht-vergessen-Liste

- [ ] ADR-0009 README-Eintrag für ADR-0014 ergänzen.
- [ ] PROJECT_STATE.md auf M4-Scope aktualisieren wenn fertig.
- [ ] Quality Gates komplett grün (pytest, ruff, format, secret-scan).
- [ ] Smoke-Test: capture → extract → ingest → approve → search "<query>" findet die Page.
- [ ] Tag `v0.5.0-search-and-browse` (nach ROADMAP-Konvention).
- [ ] Diesen Handoff bei Bedarf als „abgeschlossen" markieren.

## Quick-Recovery für Cold Start

```powershell
cd c:\projekte\curio
.\.venv\Scripts\Activate.ps1
python -m curiosity_wiki info        # zeigt Phase, Schema-Version, Source-Count
python -m pytest -q                  # erwartet: 181 passed
python tools\run_quality_gates.py    # erwartet: 4/4 OK
git log --oneline -5                 # erwartet: 99c4be4 feat(m3) zuoberst
git tag                              # erwartet: v0.4.0-wiki-review-publish
```

Falls etwas anders: PROJECT_STATE.md prüfen, dort steht der wahre Stand.
