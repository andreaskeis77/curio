# Feinkonzept Curiosity Wiki — Synthese

**Status:** Historische Referenz (Stand 2026-05-05)
**Kanonische Architekturwahrheit:** [../ARCHITECTURE_REQUIREMENTS_DOSSIER.md](../ARCHITECTURE_REQUIREMENTS_DOSSIER.md)

Dieses Dokument fasst das ursprüngliche Feinkonzept zusammen. Es enthält die Designentscheidungen und Trade-offs, die zu der aktuellen Zielarchitektur geführt haben. Bei Konflikt mit ARD/ADRs gelten ARD/ADRs.

---

## 1. Kernthese

Das Curiosity Wiki ist kein „LLM schreibt Markdown"-Projekt, sondern ein **lokaler Knowledge-Compiler mit Review-Schleife**.

> Raw Sources sind unveränderliche Belege. Das Wiki ist die lesbare Synthese. Eine Metadaten-Registry hält Zustände, Provenienz, Jobs, Claims und Qualitätsinformationen zusammen. Jede LLM-Änderung landet zuerst als überprüfbarer Draft/Patch.

## 2. Acht Architekturbausteine

1. **Stabile IDs und Registry** — Pfade allein reichen nicht. Seiten, Quellen, Jobs und Claims brauchen ULID-stabile IDs.
2. **Review Queue statt Direktmutation** — Agenten dürfen nicht direkt produktive Wiki-Seiten überschreiben.
3. **Atomic Writes und Transaktionen** — Schreibvorgänge müssen unterbrechungssicher sein.
4. **Rebuildbarkeit** — Suchindex, Linkgraph und Metadaten müssen aus Markdown/Manifests rekonstruierbar sein.
5. **Prompt-Injection-Schutz** — Webquellen sind untrusted input.
6. **UI als Produktkern** — Schmökerbarkeit, mobile Lesbarkeit, Quellenvertrauen, Orientierung.
7. **Windows-VPS-Betriebsmodell** — Deployment, Dienste, Backups, Rollback, Logs, Healthchecks früh mitdenken.
8. **Evaluationssystem** — Golden Questions, Ingest-Fidelity-Checks, Lint-Reports.

## 3. MVP-Schnitt

| MVP | Inhalt |
|---|---|
| **MVP 0** | Repo, Vault-Struktur, Schemas, ADRs, lokale Dev-Umgebung |
| **MVP 1** | Capture + Source Registry + Extracted Markdown + manuelles Review |
| **MVP 2** | LLM-Ingest erzeugt Vorschläge als Patch, nicht direkt Wiki-Seiten |
| **MVP 3** | Suche, Browse-CLI, Lint-Report, Golden Questions |
| **MVP 4** | Erste responsive Web-Oberfläche für Lesen, Suche, Quellen, Review Queue |
| **MVP 5** | Read-only Deployment auf Windows-VPS mit Backup, Healthcheck, Rollback |
| **MVP 6** | Kontrollierte Update Scouts für genau einen volatilen Bereich |

**Pilotbereiche im MVP:** UNESCO (stabil/strukturiert) + Pacojet (persönlich/methodisch). Produkttests und Haute Couture folgen.

## 4. Architekturprinzipien

- **Local-first, aber deploybar** — lokal entwickeln, später Windows-VPS read-only.
- **Markdown-first, aber nicht Markdown-only** — Markdown für Inhalte, SQLite für Operativstate, Generated Indexes für Performance.
- **Raw Sources sind immutable** — neue Snapshots bei erneutem Abruf.
- **Agents erstellen Vorschläge, keine Wahrheit** — Proposal → Review → Commit.
- **Rebuildbarkeit vor Performance** — Suchindex/Linkgraph/Backlinks/Freshness-Reports rebuildbar.
- **Qualität wird maschinenprüfbar** — id, type, status, freshness, sources Pflicht.

## 5. Datenmodell-Highlights

### IDs

| Objekt | Beispiel |
|---|---|
| Source | `src_20260505_143012_7K3P` |
| Page | `page_01HX9W2M6YK7K8E6J4N2Z7T1QK` |
| Claim | `clm_01HX9W3H7S3A9D2M8Q8J1N5A2P` |
| Proposal | `prop_20260505_150211_ingest_src_...` |
| Job | `job_01HX9W4T...` |

### Source Manifest (Pflichtfelder)

`id`, `title`, `source_type`, `original_url`, `captured_at`, `raw_path`, `extracted_path`, `sha256`, `language`, `access`, `copyright_risk`, `reliability`, `llm_allowed`, `status`, `why_interesting`.

### Page Frontmatter (Pflichtfelder)

`id`, `title`, `slug`, `type`, `status`, `created`, `updated`, `freshness`, `last_checked`, `review_after`, `confidence`, `source_policy`, `sources`, `tags`, `aliases`, `why_interesting`, `llm_generated`, `human_reviewed`, `schema_version`.

### Seitentypen

`source`, `topic`, `person`, `place`, `event`, `product_research`, `recipe`, `method`, `experiment`, `collection`, `question`.

## 6. Repo-Struktur (Empfehlung)

```text
curiosity-wiki/
  docs/                # Methodik, ADRs, Roadmap
  vault/               # raw, extracted, wiki, proposals, reports
  registry/            # SQLite Schema, Migrationen
  app/curiosity/       # Python CLI und Backend (später)
  web/                 # Frontend (später, ab M5)
  prompts/             # System, Agents, Eval
  scripts/             # PowerShell für Dev/Deploy/Backup
  tests/               # Unit, Integration, Fixtures
  eval/                # Golden Questions, Fixtures
```

In dieser Repo-Implementierung: `vault/raw` → `raw/`, `vault/wiki` → `wiki/`, etc. (flacher gehalten).

## 7. Ingest-Pipeline (7 Schritte)

```text
Capture → Extraction → Classification → Proposal Generation
       → Lint vor Review → Human Review → Commit & Index
```

## 8. Agentenmodell

| Agent | Aufgabe | Schreibt? | MVP? |
|---|---|---|---|
| Capture | Quellen registrieren | Raw + Manifest | Ja |
| Extraction | Text extrahieren | Extracted MD | Ja |
| Ingest | Wiki-Vorschläge | Proposal Store | Ja |
| Link | Verbindungen vorschlagen | Proposal Store | Teilweise |
| Lint | Struktur prüfen | Reports | Ja |
| Query | Fragen beantworten | Optional Notiz | Teilweise |
| Browse | Lesepfade | Optional Collection | Teilweise |
| Update Scout | Quellen prüfen | Proposal Store | Nach MVP |
| Refactor | Splits/Renames | Proposal Store | Später |

**Grundregel:** Agenten dürfen analysieren, vorschlagen, prüfen — niemals ungeprüft veröffentlichen.

## 9. Sucharchitektur (gestuft)

| Stufe | Technik | Wann |
|---|---|---|
| 0 | Dateisuche (ripgrep, Frontmatter) | MVP 1 |
| 1 | SQLite FTS5 | MVP 3 |
| 2 | Embeddings | später |
| 3 | Hybrid Retrieval + Reranking | später |

## 10. UI/UX-Prinzipien

1. Lesen vor Verwalten.
2. Provenienz sichtbar, aber nicht störend.
3. Mobile-first Navigation.
4. Schneller Einstieg über Home Dashboard.
5. Review als natürlicher Workflow.
6. Keine Graph-Spielerei als Kern.

**Hauptbereiche:** Home, Search/Ask, Browse, Pages, Collections, Sources, Review Queue, Open Questions, Freshness, Settings.

## 11. Windows-VPS-Deployment

- Phase D0 — Local-only.
- Phase D1 — Local Web Preview.
- Phase D2 — VPS Read-only Preview.
- Phase D3 — VPS Stable Read-only.
- Phase D4 — Admin-Funktionen optional, später.

**Erste Produktivversion:** read-only. Schreibende Agenten bleiben lokal/admin-only.

## 12. Risiken (Auszug)

| Risiko | Gegenmaßnahme |
|---|---|
| Wiki wird Link-Müllhalde | `why_interesting`, Inbox Lint, regelmäßiger Review |
| LLM halluziniert Fakten | Raw-Verweise, Claim-Marker, Review, Golden Tests |
| System wird zu komplex | MVP eng halten, CLI-first |
| Produktdaten veralten | Freshness-Modell, Update Scouts später |
| Prompt Injection | Untrusted source handling |
| Windows Deployment hakelig | Früh testen, PowerShell-Skripte, read-only zuerst |
| Copyright | Keine Volltextveröffentlichung, Source Policy |

## 13. Erste 30 Arbeitspakete (Original-Empfehlung)

Repo, Monorepo-Struktur, ADRs 0001-0003, Python CLI Skeleton, Path-Konfiguration, ID-Generator, Source/Page Schemas, SQLite Schema v1, Migration Runner, `init`/`capture file`/`capture url`, Hashing, Duplicate Detection, `sources list`, HTML/Text/PDF Extraction, `extract`, Ingest Prompt v1, LLM Client, Ingest Output Schema, Proposal Store, Diff Generator, `proposal list/show/approve/reject`, `lint` mit 5 Basisregeln.

## 14. Schlussbild

```text
Immutable Raw Sources
        +
Validated Extraction
        +
LLM Proposal Generation
        +
Human Review
        +
Versioned Markdown Wiki
        +
Registry / Search / Lint
        +
Responsive Browse UI
```

> Alles darf gesammelt werden. Aber nur Geprüftes wird dauerhaft zur Wiki-Synthese. Die Quellen bleiben Fundament, das Wiki bleibt Denkraum, und Agenten bleiben Assistenten — nicht Autoritäten.
