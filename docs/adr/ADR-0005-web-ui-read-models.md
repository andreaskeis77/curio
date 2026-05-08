# ADR-0005: Web UI mit Read Models

- **Status:** Accepted
- **Datum:** 2026-05-08
- **Tranche:** T0.1

## Kontext

Die Web-UI braucht andere Datenformen als das Markdown-Wiki:

- **Suchindex** (FTS, später Embeddings).
- **Linkgraph** für Backlinks und Navigation.
- **Site-Index** für Übersichten.
- **Page Cards** mit Vorschau-Daten.
- **Mobile Navigation** — gekürzte Hierarchie.
- **Freshness Dashboard** — aggregiert.
- **Source Trust Dashboard** — aggregiert.

Wenn die UI direkt aus `wiki/` (Markdown), `raw/` (Snapshots) oder `data/registry/` (SQLite) liest, koppelt sie sich an interne Strukturen und wird fragil.

Optionen:

- **A) Direkter Read-Through** — UI liest direkt aus Wiki/Registry.
- **B) Read Models** — separate, generierte, UI-optimierte Repräsentationen.

## Entscheidung

**Option B: Read Models. UI liest aus `read_models/` und Markdown — niemals direkt aus Raw oder Registry-Internals.**

- Read Models sind in `read_models/` als JSON/JSONL.
- Sie sind **rebuildbar** aus Markdown + Registry.
- Sie werden bei Wiki-Änderungen aktualisiert.
- Sie sind **schreibbar nur durch den Index Builder**.

```text
read_models/
  site_index.json
  graph.json
  search_documents.jsonl
  freshness_dashboard.json
  source_trust_dashboard.json
  open_questions.json
  collections.json
  mobile_nav.json
  page_cards.json
```

## Begründung

- **Entkopplung:** UI hängt nicht an internen Schemata.
- **Performance:** Pre-aggregierte Daten sind schneller als On-the-fly-Berechnung.
- **Mobile-optimiert:** Mobile-spezifische Read Models möglich (z.B. gekürzte Navigation).
- **Cacheable:** JSON-Dateien sind einfach zu cachen.
- **NEW NFL Lesson:** Read-Model-Trennung schützt UI und Kern.
- **Rebuildbar:** Bei Schema-Änderung einfach neu bauen.

## Konsequenzen

### Positiv

- Klare Architektur-Schicht.
- UI kann ohne Backend-Änderung optimiert werden.
- Read Models sind versionierbar (Schema).
- Backup einfach (alle JSONs in Snapshot).

### Negativ

- **Zusätzliche Schicht** — Index Builder.
- **Rebuild-Zeit** kann länger werden bei großem Wiki.
- **Inkonsistenz möglich** wenn Read Models nicht aktualisiert werden.

### Risiken und Mitigationen

| Risiko | Mitigation |
|---|---|
| Read Models out-of-sync mit Wiki | `curiosity rebuild-read-models`, Lint-Check, Pre-Deploy-Gate |
| Rebuild-Zeit zu lang | Inkrementeller Rebuild, optional |
| Schema-Drift zwischen Read Model und UI | Schema-Version in JSON, UI prüft |

## Build-Pipeline

```text
[1] Wiki-Änderung (z.B. neue Page nach Approval)
        ↓
[2] Trigger: rebuild-read-models
        ↓
[3] Read alle Markdown-Frontmatter
        ↓
[4] Compute graph, backlinks, search docs, freshness aggregates
        ↓
[5] Atomic write in read_models/
        ↓
[6] UI bemerkt Änderung (next request) oder via cache invalidation
```

## Verweise

- [ARCHITECTURE_REQUIREMENTS_DOSSIER.md](../ARCHITECTURE_REQUIREMENTS_DOSSIER.md) §4 (Layer 8)
- [UI_UX_GUIDE.md](../UI_UX_GUIDE.md)
- [ROADMAP.md](../ROADMAP.md) — M5
