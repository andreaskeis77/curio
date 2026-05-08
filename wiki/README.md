# wiki/

**Die kuratierten Markdown-Seiten — die menschenlesbare Wissens-Wahrheit.**

## Strukturen

```text
wiki/
  _meta/                  # Templates, Schemas, README
  sources/                # Source Pages (eine pro Raw Source)
  topics/                 # Themenseiten
  people/                 # Personen
  places/                 # Orte
  events/                 # Ereignisse
  works/                  # Werke (Bücher, Filme, Musik)
  brands/                 # Marken
  products/               # Produkt-Recherchen
  recipes/                # Rezepte
  methods/                # Methoden, Techniken
  experiments/            # Eigene Experimente
  collections/            # Sammlungen
  questions/              # Offene Fragen
```

## Frontmatter (Pflicht)

```yaml
---
id: page_01HX9W2M6YK7K8E6J4N2Z7T1QK
title: "..."
slug: "..."
type: topic | place | person | ...
status: active | draft | archived
created: 2026-05-08
updated: 2026-05-08
freshness: stable | periodic | volatile | personal
last_checked: 2026-05-08
review_after: 2026-08-08 | null
confidence: low | medium | high
source_policy: source_required_for_hard_facts
sources:
  - src_...
tags: []
aliases: []
why_interesting: "..."
llm_generated: true | false
human_reviewed: true | false
reviewed_at: 2026-05-08
schema_version: 1
---
```

## Regeln

- **Markdown-first.** Saubere Markdown-Strukturen, keine HTML-Spaghetti.
- **Wikilinks** als `[[Title]]`.
- **Externe Links** als reguläres Markdown.
- **Quellen** im Frontmatter und im Quellenpanel am Ende.
- **Harte Fakten** mit Claim-Markern (ab M3).
- **Pflichtfelder** im Frontmatter validiert via Lint.

## Werkzeuge

- **Schreiben:** Direkt in Markdown, oder über `proposal approve`.
- **Lesen:** Obsidian, VS Code, oder Web-UI (ab M5).
- **Lint:** `python -m curiosity_wiki lint`.

## Verweise

- [docs/UI_UX_GUIDE.md](../docs/UI_UX_GUIDE.md) — Layout-Prinzipien
- [docs/adr/ADR-0001-markdown-plus-sqlite-registry.md](../docs/adr/ADR-0001-markdown-plus-sqlite-registry.md)
- [_meta/](_meta/) — Templates und Schemas (kommen in M3)
