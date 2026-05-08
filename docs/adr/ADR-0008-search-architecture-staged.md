# ADR-0008: Sucharchitektur in Stufen

- **Status:** Accepted
- **Datum:** 2026-05-08
- **Tranche:** T0.1 (Strategie), Implementierung in M4 und Phase E

## Kontext

Das Curiosity Wiki braucht Suche. Mögliche Ansätze reichen von trivial (ripgrep) bis komplex (Hybrid Retrieval mit Embeddings und Reranking). Eine zu frühe Wahl der „besten" Architektur kann unnötige Komplexität einführen.

Optionen:

- **A) Sofort Vector-Database (z.B. Chroma, Qdrant)** — modern, aber komplex.
- **B) Sofort SQLite FTS5** — schnell, ausreichend für Anfang.
- **C) Stufenmodell** — beginnen mit dem Einfachsten, schrittweise erweitern.

## Entscheidung

**Option C: Stufenmodell. Wir starten mit der einfachsten Lösung und erweitern, wenn echter Bedarf entsteht.**

### Stufe 0 — Dateisuche (MVP 1)

- `ripgrep` über Markdown.
- Frontmatter-Filter über einfaches Parsing.
- Kein Index — Volltext-Scan.

### Stufe 1 — SQLite FTS5 (M4)

- Index in der Registry.
- BM25 Ranking.
- Filter nach Typ, Freshness, Tags, Status.
- Index ist rebuildbar aus Markdown.

### Stufe 2 — Embeddings (Phase E)

- Embeddings über Wiki-Seiten und Abschnitte.
- Optional: separate Embeddings für Raw Sources.
- Provider-agnostisch (sentence-transformers lokal oder OpenAI/Anthropic-Embeddings).
- Persistenz: SQLite mit `sqlite-vss` oder eigene Tabelle, alternativ separate Vector-DB.

### Stufe 3 — Hybrid Retrieval mit Reranking (Phase E+)

- BM25 + Vector Search kombiniert.
- Reranking mit Cross-Encoder oder LLM.
- Query-Rewriting.
- Source-aware Answer Generation.

## Begründung

- **Pragmatismus:** Ein gut gepflegtes Wiki mit 200 Seiten findet sich auch über `ripgrep` problemlos.
- **Komplexitäts-Vermeidung:** Vector-DBs erfordern Embeddings, Konsistenz, Updates, Indizierung — viel Wartung für wenig Mehrwert im Anfang.
- **Rebuildbarkeit:** Jede Stufe ist aus Markdown rebuildbar.
- **Schichten-Architektur:** Höhere Stufen können ältere ergänzen, nicht ersetzen.
- **Kostengünstig:** Embeddings kosten Tokens; spät einführen.

## Konsequenzen

### Positiv

- Schneller MVP.
- Wartbar.
- Erweiterbar.
- Klare Upgrade-Pfade.

### Negativ

- **Suche ist initial weniger smart** als möglich.
- Semantische Suche (z.B. "Bauwerke ähnlich der Alhambra") erst in Phase E.

### Risiken und Mitigationen

| Risiko | Mitigation |
|---|---|
| User vermisst semantische Suche | In Phase E priorisieren, sobald Wiki >100 Seiten |
| FTS5 reicht nicht für Edge Cases | Frontmatter-Filter ergänzen, Tags pflegen |
| Embedding-Modelle ändern sich | Provider-agnostisch, Version in Read Model |

## Soll-Architektur in Phase E

```text
Query → Query Rewriter (LLM)
      → BM25 Search   ─┐
      → Vector Search ─┴→ Reranker → Top K
                                   → Answer Generator (LLM, source-aware)
                                   → Strukturierter Output mit Quellen, Confidence
```

## Verweise

- [ARCHITECTURE_REQUIREMENTS_DOSSIER.md](../ARCHITECTURE_REQUIREMENTS_DOSSIER.md) §15 (offene Architekturfragen)
- [ROADMAP.md](../ROADMAP.md) — M4 und Phase E
- [concepts/feinkonzept.md](../concepts/feinkonzept.md) §11
