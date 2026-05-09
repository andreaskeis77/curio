# ADR-0016: Read-Model-Builder-Strategie

- **Status:** Accepted
- **Datum:** 2026-05-09
- **Tranche:** M5 — Local Web UI
- **Verwandt:** [ADR-0005](ADR-0005-web-ui-read-models.md) (Strategie Read Models statt Direktzugriff)

## Kontext

ADR-0005 hat festgelegt, dass die UI aus Read-Models liest, nicht direkt aus Markdown oder Registry. ADR-0016 entscheidet, **wie** diese Read-Models gebaut, geschrieben und aktuell gehalten werden.

Offene Fragen:

1. **Volle vs. inkrementelle Builds?** Bei jeder Aenderung nur ein Subset rebuilden, oder immer alles?
2. **Trigger:** automatisch beim Publish, oder explizit per CLI?
3. **Konsistenz:** wie verhindern wir, dass die UI ein veraltetes Read-Model liest?
4. **Format:** JSON vs JSONL pro Read-Model?
5. **Schema-Version:** wie wird Drift zwischen Builder und UI vermieden?

## Optionen

### Build-Strategie

- **A) Voller Rebuild bei jeder Aenderung.** Einfach, robust. Bei < 10.000 Pages performance-unkritisch.
- **B) Inkrementeller Rebuild.** Pro Read-Model nur betroffene Eintraege updaten. Komplexer, fehleranfaelliger, aber schneller.

### Trigger

- **A) Pflicht-Hook nach Publish.** Wiki und Read-Models bleiben in lock-step.
- **B) Expliziter CLI-Befehl, kein Auto-Rebuild.** Andreas kontrolliert, wann gebaut wird.
- **C) Hybrid:** Auto-Rebuild beim Publish optional, CLI immer verfuegbar.

### Konsistenz

- **A) Schema-Version pro Read-Model.** Builder schreibt `schema_version`, UI prueft beim Lesen.
- **B) Manifest-Datei.** Eine `read_models/manifest.json` mit allen Versions-Stempeln.
- **C) Keine Versions-Pruefung.** Aufpassen ohne Sicherheitsnetz.

## Entscheidung

**Voller Rebuild, expliziter CLI-Trigger, Schema-Version pro Read-Model.**

### Build-Strategie: voller Rebuild

- `curiosity readmodels rebuild` baut alle Read-Models von Grund auf.
- Wiki ist klein (< 1000 Pages absehbar), Build dauert < 1 Sekunde.
- Inkrementelle Builds werden erst eingefuehrt, wenn das tatsaechlich noetig wird (Phase A).
- Atomic per Read-Model: temp-file schreiben, dann `os.replace`. So bleibt die UI lesbar, falls der Build mittendrin abbricht.

### Trigger: expliziter CLI

- Im MVP **kein** Auto-Hook beim Publish.
- Begruendung: Read-Models sind ein Snapshot, der vor dem Web-Serving aktualisiert wird. Kopplung an Publish wuerde jeden Approve teurer machen.
- Workflow: nach mehreren Approves einmal `curiosity readmodels rebuild`, dann `curiosity web run`.
- Auto-Hook beim Publish kann spaeter optional ueber `CURIOSITY_READMODELS_AUTO_REBUILD=true` aktiviert werden.

### Konsistenz: Schema-Version pro Read-Model

Jedes Read-Model traegt im JSON ein `meta`-Objekt:

```json
{
  "meta": {
    "schema_version": 1,
    "built_at": "2026-05-09T19:30:00Z",
    "wiki_pages_count": 42,
    "builder_version": "0.5.0"
  },
  "data": [...]
}
```

Die UI prueft beim Laden `schema_version` und meldet einen Fehler, wenn die erwartete Version abweicht.

### Format: JSON pro Read-Model, ausser ``search_documents``

- **JSON** fuer alles, was als Ganzes geladen wird (Manifest plus Daten).
- **JSONL** fuer ``search_documents.jsonl`` — Streaming-faehig, falls in Phase E die Anzahl deutlich waechst.

### Read-Model-Inventar (M5)

- ``site_index.json`` — Liste aller veroeffentlichten Pages mit Title, Slug, Type, Freshness, Status, Pfad. Fuer Top-Level-Navigation und Such-Auto-Suggest spaeter.
- ``graph.json`` — Adjazenz-Liste der ``links``-Tabelle. Fuer Backlinks-/Forward-Links-Visualisierung.
- ``search_documents.jsonl`` — pro Page ein Dokument mit ``id``, ``title``, ``body_excerpt`` (max 800 Zeichen), ``tags``. Optional fuer alternative Suchpfade ausserhalb FTS.
- ``freshness_dashboard.json`` — Buckets ``overdue``, ``due_within_7_days``, ``volatile_without_schedule``. Direkt aus ``collect_freshness_status``.
- ``page_cards.json`` — pro Page ein Card-Objekt mit Title, Snippet (300 Zeichen), Type, Freshness, Confidence, Tags, Backlinks-Count. Fuer Listen und Home-Sektionen.
- ``mobile_nav.json`` — gekuerzte Navigation fuer Mobile: Top-Level-Topics, Collections, Recent Updates.
- ``open_questions.json`` — Aggregation aus ``collect_open_questions``.

Die ROADMAP nennt zusaetzlich ``source_trust_dashboard.json`` und ``collections.json``. Die werden in M5 nicht gebaut — sie sind in Phase B/C besser aufgehoben, wenn entsprechender Content vorhanden ist.

## Begründung

- **Voller Rebuild ist einfach und richtig** fuer aktuelle Groessenordnung. Komplexitaet vermeiden, bevor sie Mehrwert bringt.
- **Expliziter CLI-Trigger** macht den Snapshot-Charakter sichtbar und erlaubt Andreas, Builds zu groupen.
- **Schema-Version** ist die Mindest-Sicherheit, damit Read-Model und UI nicht stillschweigend auseinanderlaufen.
- **JSON ueberall** ausser bei JSONL-natives — niedrige Werkzeug-Anforderungen.

## Konsequenzen

### Positiv

- Read-Models sind klar als Build-Artefakt erkennbar.
- Test- und Diff-friendly (JSON-Diff bei Aenderungen einsehbar).
- UI muss nur ``read_models/*.json`` lesen koennen.
- Atomic Schreiben verhindert Halb-Zustaende.

### Negativ

- Bei Publish ohne anschliessenden Rebuild ist die UI veraltet, bis Andreas baut. Mitigation: `info`-CLI zeigt `read_models_built_at`, Linter koennte spaeter eine Regel haben.

### Risiken und Mitigationen

| Risiko | Mitigation |
|---|---|
| Vergessener Rebuild fuehrt zu veralteter UI | `info`-CLI zeigt Builder-Stempel; M6 Pre-Deploy-Gate fordert frische Read-Models |
| Schema-Drift zwischen Builder und UI | `meta.schema_version` in jedem Read-Model, UI prueft |
| Build-Abbruch waehrend Schreibens | Atomic write (temp + os.replace) pro File |
| Read-Model-Inhalt enthaelt private Notizen | M6 Publish-Bundle filtert private Sources, Read-Models ignorieren ``page.status='draft'`` |

## Folge-Aenderungen

- **`src/curiosity_wiki/read_models/builder.py`** — alle Builder-Funktionen.
- **`src/curiosity_wiki/read_models/__init__.py`** — Public API.
- **CLI:** `curiosity readmodels rebuild`, `curiosity readmodels status`.
- **Tests:** `tests/test_read_models.py`.

## Verweise

- [ADR-0005](ADR-0005-web-ui-read-models.md) — Read-Models-Strategie
- [ADR-0014](ADR-0014-search-stage-1-fts5-implementation.md) — FTS-Konsistenz-Pattern als Vorbild
- [ROADMAP.md](../ROADMAP.md) — M5
