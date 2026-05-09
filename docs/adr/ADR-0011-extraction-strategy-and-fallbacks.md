# ADR-0011: Extraction-Strategie und Fallbacks

- **Status:** Accepted
- **Datum:** 2026-05-08
- **Tranche:** M2 — Extraction & Proposal Ingest

## Kontext

Quellen kommen in heterogenen Formaten: HTML (mit/ohne Boilerplate), PDF (text-basiert oder gescannt), Markdown, einfacher Text, CSV/JSON.

Ziele für die Extraktion:

- **Lesbarer Markdown-Text** als Input für LLM-Synthese.
- **Verlässliches Verhalten** — kein Crash bei kaputten Inputs.
- **Idempotenz** — wiederholte Extraktion gleicher Snapshot ergibt gleiches Ergebnis (modulo Library-Versionen).
- **Versionierte Extraktoren** — Replay erfordert klare Provenienz.

## Optionen

- **A) Eine Library für alles** (z.B. `markitdown`). Mächtig aber schwere Dependency.
- **B) Pro Format eine spezialisierte Library** mit klaren Fallbacks.
- **C) Eigene Parser.** Zu viel Aufwand, fehleranfällig.

## Entscheidung

**Option B: Pro-Format-Adapter mit definierten Fallbacks.**

### Format-Pipeline

| Source-Type | Primary Extractor | Fallback | Library |
|---|---|---|---|
| `web` (HTML) | `trafilatura.extract` mit Markdown-Output | Plaintext-Strip aus HTML | `trafilatura` |
| `pdf` | `pypdf` Page-Text | Fehler markieren, manuelle Extraktion | `pypdf` |
| `note` (Markdown) | Passthrough | — | stdlib |
| `file` (Text) | Encoding-detect → Text | Hex-Preview bei Binärinhalt | stdlib |
| `data` (CSV/JSON) | JSON pretty-print / CSV-Header | Raw-Pass-Through | stdlib |
| `screenshot` | **Skip** — OCR später (Phase B/E) | — | — |

### Output

Pro extrahierter Source eine Datei `extracted/<source_id>.md`:

```markdown
---
source_id: src_...
extractor: trafilatura
extractor_version: "2.0.0"
extracted_at: 2026-05-08T20:30:00+00:00
input_sha256: <hash der raw datei>
warnings:
  - "..."
---

# Original Title (falls erkannt)

<extrahierter Text>
```

### Statusmaschine

```text
SourceStatus.CAPTURED
        ↓
   extract <source_id>
        ↓
SourceStatus.EXTRACTED   (success path)
        ↓
SourceStatus.CLASSIFIED  (after ingest)
```

Fehlerpfade:

- `extraction_failed` (vermerkt in `extractions.status` und `sources.status`).
- Re-run hebt den Fehler nicht auf — die Quelle bleibt `extraction_failed`, bis manueller Eingriff oder erfolgreicher Re-Run.
- `quarantined` bei verdächtigem Content (Prompt Injection — siehe ADR-0010 + Quarantäne-Logik).

### Tabelle `extractions`

```sql
CREATE TABLE extractions (
    id              TEXT PRIMARY KEY,         -- ext_<run_id>
    source_id       TEXT NOT NULL,
    extractor       TEXT NOT NULL,            -- trafilatura | pypdf | passthrough | text
    extractor_version TEXT NOT NULL,
    input_sha256    TEXT NOT NULL,            -- aus source_snapshots
    output_path     TEXT,                     -- extracted/<source_id>.md (relativ)
    output_sha256   TEXT,
    output_chars    INTEGER,
    status          TEXT NOT NULL,            -- extracted | failed | empty
    started_at      TEXT NOT NULL,
    finished_at     TEXT,
    warnings_json   TEXT,                     -- JSON-Array
    error_message   TEXT,
    FOREIGN KEY (source_id) REFERENCES sources(id) ON DELETE CASCADE
);
```

### Idempotenz

- `extract <source_id>` schreibt immer eine neue Zeile in `extractions` mit eigenem `id`.
- Die Output-Datei wird **überschrieben**, da Extraktion regenerierbar ist.
- Wenn `input_sha256` dem letzten erfolgreichen Lauf entspricht und der Extractor unverändert ist, ist ein Re-Run optional.

### Prompt-Injection-Vorscan

Vor LLM-Übergabe prüft ein einfacher Heuristik-Scanner den extrahierten Text auf injection-typische Muster:

- `Ignore all previous instructions`
- `You are now <role>`
- `Disregard your system prompt`
- `<|...|>` Tag-Sequenzen
- Direkte Aufforderungen an „den Assistenten"

Findings landen in `quarantine_cases` mit `case_type=prompt_injection` und blockieren den Ingest, bis der User entscheidet.

## Begründung

- **Trafilatura** ist Stand der Technik für Web-Boilerplate-Removal und liefert gleich Markdown.
- **pypdf** reicht für Text-PDFs; gescannte Bilder sind explizit Phase-B-Thema.
- **Passthrough** für Markdown ist die einfachste mögliche Implementierung.
- **Pre-LLM-Scan** verhindert, dass eine bösartige Quelle den Agent kapert (NEW NFL Quarantäne-Pattern).
- **Atomic Write** des extrahierten Markdown via temp + rename.

## Konsequenzen

### Positiv

- Klare Verantwortung pro Format.
- Fehler in einem Format zerstören andere Formate nicht.
- Erweiterbarkeit (OCR, MS-Office) ist eine eigene Tranche.
- Replay ist möglich, weil `extractor_version` gespeichert wird.

### Negativ

- Drei Extraktor-Libraries als Hard-Dependency.
- pypdf kann mit komplexen Layouts kämpfen.
- Trafilatura sieht große HTML-Pages als single string — Memory-Limit ggf. relevant.

### Risiken und Mitigationen

| Risiko | Mitigation |
|---|---|
| Library-Update bricht Output | `extractor_version` in Run Evidence; Golden-Tests |
| Sehr große PDFs/HTML | Limit von 50 MB; größere Files in Quarantäne |
| Prompt Injection unentdeckt | Heuristik + LLM-System-Regel + manueller Review |
| Encoding-Probleme | UTF-8 + BOM-Strip; Fallback auf chardet später |

## Verweise

- [ADR-0010](ADR-0010-llm-client-wrapper-implementation.md)
- [SECURITY.md](../SECURITY.md) — Prompt Injection
- [SOURCE_POLICY.md](../SOURCE_POLICY.md)
- [TEST_STRATEGY.md](../TEST_STRATEGY.md) — Golden Tests, Ingest Fidelity
