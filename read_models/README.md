# read_models/

UI-optimierte, **rebuildbare** Repräsentationen des Wiki-Inhalts.

## Inhalt (ab M5)

```text
read_models/
  site_index.json              # Liste aller Seiten mit Metadaten
  graph.json                   # Linkgraph
  search_documents.jsonl       # Suchdokumente (BM25/FTS-tauglich)
  freshness_dashboard.json     # Aggregat: Seiten mit überschrittenem review_after
  source_trust_dashboard.json  # Aggregat: Reliability-Verteilung
  open_questions.json          # Aggregat: alle question-Pages
  collections.json             # Aggregat: alle collection-Pages
  mobile_nav.json              # Vereinfachte Mobile-Navigation
  page_cards.json              # Vorschau-Karten für Home Dashboard
```

## Regeln

- **Rebuildbar** aus Markdown + Registry — `curiosity rebuild-read-models`.
- **Schreibbar** nur durch Index Builder, niemals direkt durch UI.
- **Atomic Writes** — temp file, fsync, atomic rename.
- **Schema-versioniert** — jede Datei enthält `schema_version`.
- Inhalt ist gitignored.

## Verweise

- [docs/adr/ADR-0005-web-ui-read-models.md](../docs/adr/ADR-0005-web-ui-read-models.md)
- [docs/ARCHITECTURE_REQUIREMENTS_DOSSIER.md](../docs/ARCHITECTURE_REQUIREMENTS_DOSSIER.md) §4
