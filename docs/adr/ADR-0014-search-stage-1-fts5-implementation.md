# ADR-0014: Sucharchitektur Stufe 1 — FTS5-Implementierung

- **Status:** Accepted
- **Datum:** 2026-05-09
- **Tranche:** M4 — Browse, Search, Lint
- **Verwandt:** [ADR-0008](ADR-0008-search-architecture-staged.md) (Strategie Stufenmodell)

## Kontext

ADR-0008 hat das Stufenmodell festgelegt: Stufe 0 (`ripgrep`), Stufe 1 (SQLite FTS5 in M4), Stufe 2 (Embeddings, Phase E), Stufe 3 (Hybrid Retrieval). M4 implementiert nun Stufe 1.

Offene Detail-Fragen:

1. **FTS5-Tabellen-Layout:** virtuelle Tabelle mit `content=pages` (Auto-Sync via Triggers), externe `content=''` (contentless) oder eigenständige `pages_fts`-Tabelle, die manuell mitgeschrieben wird?
2. **Welche Felder?** Titel und Body sind Pflicht — was ist mit Tags, Aliases, Section-Headings, Why-Interesting?
3. **Body-Persistenz:** `pages` speichert keinen Body, nur den Pfad zum Markdown-File. Body kommt aus dem File. Wo liegt die Wahrheit für FTS?
4. **Filter (`type`, `status`, `freshness`, `tags`):** im FTS-MATCH oder per Join auf `pages`?
5. **Index-Rebuild:** wie hält man FTS und Wiki-Markdown bei manuellen Edits oder nach `git pull` konsistent?

## Optionen

### Tabellen-Layout

- **A) `content=pages`** mit Triggers: SQLite hält FTS automatisch synchron mit der `pages`-Tabelle. Setzt voraus, dass `pages` die zu indizierenden Felder enthält. Body ist nicht in `pages` — daher müssten wir eine `body_text`-Spalte ergänzen.
- **B) Contentless `content=''`:** FTS-Tabelle speichert nichts auf eigene Faust, Caller muss `rowid` + Daten passend einfügen und konsistent halten.
- **C) Eigenständige FTS5-Tabelle:** Spalten enthalten Inhalt wie eine normale Tabelle. Kein Trigger-Magie, manuelles Befüllen beim Publish und beim Rebuild. Storage-Overhead ist tolerabel (Wiki ist klein, < ein paar MB Text).

### Filter

- **Inline im FTS-MATCH:** schwer kontrollierbar, weil MATCH nur Volltext-Suche kennt.
- **Per Join auf `pages`:** sauber, FTS bleibt nur Volltext, Filter sind SQL-Standard.

### Index-Rebuild

- **Aus `pages` + Markdown-Files**: für jede Page in der Registry den Body aus der Markdown-Datei lesen und neu in FTS einfügen.
- **Nur aus `pages` (mit body-Spalte)**: schneller, aber doppelte Wahrheit — wenn jemand Markdown manuell editiert, ist FTS veraltet, bis Rebuild läuft.

## Entscheidung

**Eigenständige FTS5-Tabelle `pages_fts`, Filter per Join auf `pages`, Rebuild aus Wiki-Markdown.**

### `pages_fts` Schema (Migration 0004)

```sql
CREATE VIRTUAL TABLE IF NOT EXISTS pages_fts USING fts5(
    page_id UNINDEXED,
    title,
    body,
    tags,
    why_interesting,
    tokenize = 'unicode61 remove_diacritics 1'
);
```

- `page_id UNINDEXED`: liefert beim Hit die Page-ID, wird selbst nicht durchsucht.
- `title`, `body`, `tags`, `why_interesting`: durchsuchbare Spalten. Tags und Why-Interesting helfen bei Schlagwort- und Themen-Queries.
- `tokenize='unicode61 remove_diacritics 1'`: Umlaute und Akzente werden normalisiert. Damit findet ``"Stätte"`` auch ``"Statte"``.

### Pflege-Regeln

- **Beim Publish:** Page wird in `pages` eingefügt und gleichzeitig in `pages_fts` mit Body aus dem geschriebenen Markdown-File. Re-Publish (M4 nicht implementiert, aber zukünftig): erst `DELETE FROM pages_fts WHERE page_id=?`, dann Insert.
- **Bei Reject / Request-Changes:** kein FTS-Schreibvorgang.
- **Rebuild:** `curiosity index rebuild` löscht `pages_fts` komplett und befüllt es aus allen `wiki/**/*.md` mit Frontmatter neu. Kein Sync gegen `pages` (Markdown ist die Wahrheit, ADR-0001).

### Filter

`search`-CLI nimmt `--type`, `--status`, `--freshness`, `--tag`, `--limit` an. Query-Form:

```sql
SELECT p.id, p.title, p.type, p.freshness, p.status,
       bm25(pages_fts) AS rank,
       snippet(pages_fts, 2, '<<', '>>', '...', 12) AS snippet
FROM pages_fts
JOIN pages p ON p.id = pages_fts.page_id
WHERE pages_fts MATCH ?
  AND (? IS NULL OR p.type = ?)
  AND (? IS NULL OR p.freshness = ?)
  AND (? IS NULL OR p.status = ?)
ORDER BY rank
LIMIT ?;
```

### Index-Rebuild-Algorithmus

1. `DELETE FROM pages_fts;`
2. Für jede `wiki/**/*.md` (außer `_meta`/`README.md`):
   - Frontmatter parsen.
   - `page_id`, `title`, `tags`, `why_interesting` aus Frontmatter; `body` aus Markdown nach Frontmatter.
   - `INSERT INTO pages_fts(page_id, title, body, tags, why_interesting) VALUES (?, ?, ?, ?, ?);`.
3. Liefert Statistik: gefundene Files, geschriebene Rows, übersprungene (z.B. ohne valides Frontmatter).

Wichtig: der Rebuild **liest Markdown, nicht die `pages`-Tabelle** — damit ist FTS auch nach manuellen Edits konsistent rebuildbar.

## Begründung

- **Eigenständige Tabelle** ist robust und nachvollziehbar. Triggers auf `pages` mit `content=pages` würden eine `body`-Spalte in `pages` erzwingen — das vermischt Markdown-Wahrheit (Datei) und Registry (operativer Zustand). ADR-0001 trennt das bewusst.
- **Contentless FTS5** spart wenig Storage (Wiki ist klein) und macht Snippet-Generation (`snippet()`) schwierig.
- **Filter per Join** trennt Volltext-Ranking von strukturellen Filtern. SQL bleibt lesbar; FTS-MATCH bleibt fokussiert.
- **Rebuild aus Markdown** ist die einzige Garantie für Konsistenz nach manuellen Edits. Performance ist unkritisch — Wiki bleibt unter ein paar Tausend Pages.
- **Tokenizer mit `remove_diacritics`** entspricht der deutschsprachigen Realität (UNESCO-Stätte, Pacojet, etc.).

## Konsequenzen

### Positiv

- FTS-Konsistenz nach `git pull` per `index rebuild` herstellbar.
- Filter sind SQL-Standard, leicht erweiterbar.
- Kein Trigger-Voodoo, klare Schreibpfade beim Publish.

### Negativ

- Doppelte Schreibvorgänge beim Publish: Markdown-File + Registry + FTS. Bei Fehler im FTS-Insert kann Inkonsistenz entstehen — Mitigation: Rebuild ist immer eine Option, FTS-Insert in derselben Transaktion wie `pages.insert`.
- Keine Auto-Sync — wer manuell `pages.delete` macht, muss `pages_fts.delete` ebenfalls auslösen. M4 hat noch keinen Page-Delete-Pfad, daher nicht akut.

### Risiken und Mitigationen

| Risiko | Mitigation |
|---|---|
| FTS5 in der lokalen SQLite-Build nicht aktiviert | Migration prüft beim Start (`CREATE VIRTUAL TABLE` schlägt früh fehl); Smoke-Test im Cold-Start |
| Snippet zerschneidet Wikilinks (`[[...]]`) ungünstig | `snippet()`-Margin angemessen wählen, akzeptierter Trade-off |
| Manuelle Markdown-Edits laufen aus der DB | `index rebuild` als Pflichtschritt nach `git pull` |
| Body-Größe pro Page wird groß | FTS5 verträgt das; ggf. später Sektions-Indexierung in Phase E |

## Folge-Änderungen

- **Migration 0004:** `pages_fts` virtuelle Tabelle.
- **`wiki/publish.py`:** in Phase B FTS-Insert ergänzen.
- **`search/`-Modul:** `search_pages(query, *, type, freshness, status, tag, limit)`.
- **`search/index.py`:** `rebuild_index_from_markdown(paths, conn)`.
- **CLI:** `curiosity search "<query>"`, `curiosity index rebuild`.

## Verweise

- [ADR-0001](ADR-0001-markdown-plus-sqlite-registry.md) — Markdown + SQLite Trennung
- [ADR-0008](ADR-0008-search-architecture-staged.md) — Stufenmodell-Strategie
- [ADR-0009](ADR-0009-registry-schema-versioning.md) — Migrations-Konvention
- [ROADMAP.md](../ROADMAP.md) — M4
