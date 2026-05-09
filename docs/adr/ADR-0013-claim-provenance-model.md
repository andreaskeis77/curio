# ADR-0013: Claim-Provenienz-Modell

- **Status:** Accepted
- **Datum:** 2026-05-09
- **Tranche:** M3 — Review & Publish

## Kontext

Eine Wiki-Seite enthält Mischungen aus:

- **Synthese** (Eigenformulierungen des Wikis, basierend auf Quellen).
- **Harten Fakten** (Zahlen, Datumsangaben, Preise, Spezifikationen, Zitaten).
- **Interpretation** (Andreas' eigenen Schlüssen).

Bei harten Fakten ist die **Quellenbindung** kritisch: Wenn der Inhalt der Quelle sich später ändert oder als falsch herausstellt, müssen alle abhängigen Aussagen aufgespürt werden können.

## Optionen

- **A) Granulare Claim-Tracking auf Satz-Ebene** mit Inline-Markern (`[[claim:clm_...]]`) — präzise, aber pflegeintensiv.
- **B) Claim-Tracking nur für „harte Fakten"** mit Footer-Verweisen pro Page — pragmatisch.
- **C) Kein Claim-Tracking, nur Page-Level-Sources** — einfach, aber unzureichend für Audit.

## Entscheidung

**Option B: Claim-Tracking für harte Fakten, Page-Level-Sources für alles andere.**

### Datenmodell

#### Tabelle `claims`

```sql
CREATE TABLE claims (
    id              TEXT    PRIMARY KEY,        -- clm_<ULID>
    page_id         TEXT    NOT NULL,
    claim_text      TEXT    NOT NULL,
    claim_type      TEXT    NOT NULL,           -- year | number | price | spec | quote | location | percent | other
    source_id       TEXT    NOT NULL,
    source_locator  TEXT,                       -- z.B. "page 3" oder "section 2.1"
    confidence      TEXT    NOT NULL,           -- low | medium | high
    verified_at     TEXT,
    proposal_id     TEXT,
    created_at      TEXT    NOT NULL,
    updated_at      TEXT    NOT NULL,
    FOREIGN KEY (page_id)   REFERENCES pages(id)    ON DELETE CASCADE,
    FOREIGN KEY (source_id) REFERENCES sources(id),
    FOREIGN KEY (proposal_id) REFERENCES proposals(id)
);

CREATE INDEX idx_claims_page    ON claims(page_id);
CREATE INDEX idx_claims_source  ON claims(source_id);
CREATE INDEX idx_claims_type    ON claims(claim_type);
```

#### Tabelle `page_sources`

```sql
CREATE TABLE page_sources (
    page_id    TEXT NOT NULL,
    source_id  TEXT NOT NULL,
    relation   TEXT NOT NULL,           -- primary | supporting | derived
    PRIMARY KEY (page_id, source_id),
    FOREIGN KEY (page_id)   REFERENCES pages(id)    ON DELETE CASCADE,
    FOREIGN KEY (source_id) REFERENCES sources(id)
);
```

### Claim-Marker im Markdown

Pro Claim wird im Markdown ein knapper Inline-Hinweis gerendert (kein Inline-HTML, damit Obsidian-kompatibel):

```markdown
Die Stätte wurde 1984 in die UNESCO-Welterbeliste aufgenommen.
[Quelle: src_20260509_unesco_alhambra]
```

Die ausführliche Claim-Provenienz lebt in der Registry — der Markdown bleibt lesbar und nicht überfrachtet.

### Pflicht-Claims

Im MVP gilt: **harte Fakten brauchen Quellenbindung.** Lint meldet ungebundene Aussagen (heuristisch erkannt) als `claim_missing_source`.

Welche Aussagen als „harter Fakt" gelten:

- Jahreszahlen (`\b(19|20)\d{2}\b`)
- Geldbeträge (`\b\d+([,.]\d+)?\s?(€|EUR|USD|\$)\b`)
- Prozentangaben (`\b\d+([,.]\d+)?\s?%`)
- Direkte Zitate (`[„""].{20,}["""]`)

### Schreibweise im Proposal-Output

Der LLM liefert in `IngestProposalV1.hard_facts` strukturierte Claim-Vorschläge. Beim Publish:

- Pro `HardFact` wird ein `claims`-Eintrag erzeugt.
- Der Inline-Marker im Markdown wird automatisch generiert (basierend auf `claim_text` + `source_id`).

### Confidence

- `high`: mehrere unabhängige Quellen bestätigen die Aussage, oder offizielle Quelle.
- `medium`: eine plausible Quelle.
- `low`: eine unsichere Quelle, oder Interpretation/Notiz.

Confidence wird sowohl pro Claim als auch pro Page geführt — Page-Confidence ist konservativ das Minimum aller Claim-Confidences plus Synthese-Bewertung.

## Begründung

- **Pragmatisch**: Granulare Claim-Tracking auf Satz-Ebene ist zu pflegeintensiv für ein persönliches Wiki.
- **Auditierbar**: Bei Quellen-Update oder Fakt-Korrektur kann via SQL alle abhängigen Claims gefunden werden.
- **Lint-erfassbar**: Heuristik findet ungebundene Fakten — nicht perfekt, aber Frühwarnung.
- **Obsidian-kompatibel**: Inline-Marker bleiben als Markdown lesbar, kein HTML-Komplex.

## Konsequenzen

### Positiv

- Quellen-Audit per SQL möglich.
- Lint findet ungebundene Fakten.
- Claim-Update bei Quellen-Korrektur ist zielgerichtet.

### Negativ

- Heuristik erkennt nicht jeden harten Fakt.
- LLM kann harte Fakten falsch klassifizieren.
- Manuell hinzugefügte Inhalte (außerhalb Proposal-Workflow) brauchen manuelle Claim-Pflege.

### Risiken und Mitigationen

| Risiko | Mitigation |
|---|---|
| LLM erkennt harte Fakten nicht | Lint findet ungebundene Aussagen heuristisch |
| Quellen-Update bricht Verlinkung | `claims.source_id` ist FK — Source-Löschung per Default verboten |
| Inline-Marker im Markdown stören Lesefluss | Marker bewusst kurz; alternative Frontmatter-Liste optional in M4 |

## Verweise

- [ADR-0001](ADR-0001-markdown-plus-sqlite-registry.md) — Markdown + SQLite
- [ADR-0010](ADR-0010-llm-client-wrapper-implementation.md) — IngestProposalV1.hard_facts
- [ROADMAP.md](../ROADMAP.md) — M3
