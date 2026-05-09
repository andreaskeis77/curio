# ADR-0019: Update-Scout-Modell

- **Status:** Accepted
- **Datum:** 2026-05-09
- **Tranche:** M7 — First Update Scout
- **Verwandt:** [ADR-0003](ADR-0003-agent-proposals-not-direct-writes.md) (Agenten erzeugen Proposals), [ADR-0006](ADR-0006-source-policy-and-copyright-boundaries.md) (Source-Policy)

## Kontext

M7 baut den ersten Update-Scout: ein periodischer Job, der definierte Quellen prueft und bei Aenderungen automatisch ein Update-Proposal erzeugt. Der Scout soll **nicht** direkt nach `wiki/` schreiben — er nutzt den bestehenden Proposal-Workflow (M2/M3).

Anforderungen:

- **Read-only auf das Wiki**: Scout produziert Proposals, nie Direkt-Aenderungen.
- **Whitelist-basiert**: nur explizit aufgefuehrte Quellen werden angefasst.
- **Deduplikations-sicher**: gleiche Quelle nicht zweimal capturen, wenn der Inhalt unveraendert ist (SHA-256-Vergleich).
- **Quarantaene-fest**: bei Prompt-Injection-Verdacht oder Schema-Drift gleiche Eskalation wie bei manuellem Ingest.
- **Doppellauf-sicher**: zwei parallele Scout-Runs auf der gleichen Definition duerfen sich nicht ins Gehege kommen.
- **Auditierbar**: jeder Run hat eine `run_id`, ein Markdown-Log und einen DB-Eintrag.
- **Andreas-Laptop, nicht VPS**: M7 laeuft lokal, weil die VPS read-only ist (ADR-0017).

Offene Fragen:

1. **Quellen-Format**: nur URLs, oder auch lokale Notes/Files?
2. **Lock-Mechanik**: File-Lock, DB-Lock, oder PID-File?
3. **Frequenz**: in der YAML, oder ueber Windows-Scheduled-Task?
4. **Inkrementell vs. voll**: pro Run alle Quellen, oder nur die mit ueberschrittenem `next_run_at`?

## Optionen

### Quellen-Format

- **A) Nur URLs**: passt zu klassischen Scouts. Reicht initial nicht, weil wir lokale Test-Fixtures brauchen.
- **B) URL + note + file**: Reuse der bestehenden `capture_*`-Funktionen. Tests koennen `note`-Quellen nutzen, Production `url`.

### Lock-Mechanik

- **A) PID-Lock-File** in `data/scout_locks/<scout_id>.lock`. Stale-Detection ueber PID-Existenz und Timestamp.
- **B) DB-Lock** (advisory): `INSERT INTO scout_runs(status='running')`. Risiko: bei Crash bleibt es haengen, manuelles Cleanup noetig.
- **C) Beides**: PID-File primaer, DB-Tabelle fuer Audit.

### Frequenz

- **A) In der YAML** (`frequency_hours: 24`). Skript prueft `last_run_at` und entscheidet.
- **B) Im Scheduled-Task**. Skript laeuft immer.
- **C) Hybrid**: `frequency_hours` als Soll-Mindestabstand, Scheduled-Task als Trigger. Skript bricht ab, wenn `last_run < frequency_hours`.

## Entscheidung

**URL + note + file als Quellen-Format, PID-File-Lock + DB-Audit, Hybrid-Frequenz, voller Run pro Trigger.**

### Scout-YAML-Schema

```yaml
id: unesco-welterbe              # eindeutiger Bezeichner, Pflicht
domain: places                   # Kategorie / Pilotbereich
description: |
  Periodische Pruefung der UNESCO-Welterbe-Eintraege im Wiki gegen
  bekannte Listen-Quellen.
prompt_id: ingest_v0_1           # Prompt aus prompts/agents/
frequency_hours: 168             # 1x pro Woche (default 24)
sources:
  - type: url                    # url | note | file
    value: https://example.org/listing  # bei type=url
    why_interesting: "UNESCO-DE-Listing"
  - type: note
    value: |
      Stand 2026-05: 51 deutsche Welterbestaetten gelistet.
    why_interesting: "Eigene Notiz"
limits:
  max_sources_per_run: 10        # Hard-Limit, default 20
  llm_allowed: true              # default true
  dry_run: false                 # default false
quarantine:
  on_injection: true             # default true (siehe ADR-0010)
  on_schema_drift: true
```

### Pflichtfelder

`id`, `domain`, `prompt_id`, `sources` (mind. 1 Eintrag mit `type` und `value`).

### Defaults

- `frequency_hours`: 24
- `description`: leer
- `limits.max_sources_per_run`: 20
- `limits.llm_allowed`: true
- `limits.dry_run`: false
- `quarantine.on_injection`: true
- `quarantine.on_schema_drift`: true

### Pipeline

```text
[1] curiosity scout run <id>  (CLI oder Scheduled-Task)
       ↓
[2] Lock-File akquirieren (PID + Timestamp). Stale-Lock (> 1h) wird uebernommen.
       ↓
[3] last_run_at aus scout_runs lesen. Wenn jetzt - last_run < frequency_hours
    und nicht --force: Abbruch mit "skipped: too soon".
       ↓
[4] Pro Source in Whitelist:
       a. Hash der Inhalte berechnen, gegen sources.sha256 vergleichen.
          Bei Match: skip ("unchanged").
       b. capture_url/note/file aufrufen.
       c. extract_source.
       d. ingest_source mit Scout-Prompt.
       e. Bei Quarantaene: case anlegen, weiter mit naechster Source.
       ↓
[5] scout_runs-Eintrag mit Counts (sources_seen, captured, proposals,
    quarantined, errors) und finished_at schreiben.
       ↓
[6] Run-Log nach docs/_ops/scout_runs/<run_id>.md schreiben.
       ↓
[7] Lock-File freigeben.
```

### Lock-File-Mechanik

- Pfad: `data/scout_locks/<scout_id>.lock`
- Inhalt: JSON `{"pid": <int>, "started_at": "<iso>", "host": "<name>"}`
- Akquise: `O_CREAT | O_EXCL` (Python: `Path.open("x")`).
- Stale-Detection: wenn Lock existiert, aber `started_at` > 1h alt **oder** PID lebt nicht mehr → uebernehmen.
- Freigabe: `unlink` im finally-Block.

### Lock-File: kein Auto-Release durch DB-Tabelle

`scout_runs.status='running'` ist nur Audit, nicht Lock. Bei Crash bleibt der Status haengen — Cleanup-Skript markiert sie nach 1h als `crashed`.

### Quarantaene-Verhalten

Reuse aus M2. Wenn `quarantine.on_injection=true` (Default) und die Pre-LLM-Heuristik schlaegt an, wird der Scout weiterlaufen mit der naechsten Source — keine Abbruch-Eskalation.

### Run-Log-Format

```markdown
# Scout Run <run_id>

**Scout:** unesco-welterbe
**Started:** 2026-05-09T03:00:00Z
**Finished:** 2026-05-09T03:00:42Z
**Status:** completed | skipped | failed

## Counts

| metric | value |
|---|---|
| sources_seen | 5 |
| captured | 2 |
| skipped_unchanged | 3 |
| proposals | 2 |
| quarantined | 0 |
| errors | 0 |

## Sources

| source | action | proposal_id |
|---|---|---|
| https://… | captured + proposal | prop_xyz |
| (note) | unchanged | — |
```

### scout_runs-Tabelle (Migration 0005)

```sql
CREATE TABLE scout_runs (
    id              TEXT PRIMARY KEY,        -- sr_<ULID>
    scout_id        TEXT NOT NULL,
    started_at      TEXT NOT NULL,
    finished_at     TEXT,
    status          TEXT NOT NULL,           -- running | completed | skipped | failed | crashed
    sources_seen    INTEGER NOT NULL DEFAULT 0,
    captured        INTEGER NOT NULL DEFAULT 0,
    skipped         INTEGER NOT NULL DEFAULT 0,
    proposals       INTEGER NOT NULL DEFAULT 0,
    quarantined     INTEGER NOT NULL DEFAULT 0,
    errors          INTEGER NOT NULL DEFAULT 0,
    log_path        TEXT,                    -- relativer Pfad zum MD-Log
    error_message   TEXT
);

CREATE INDEX idx_scout_runs_scout ON scout_runs(scout_id);
CREATE INDEX idx_scout_runs_started ON scout_runs(started_at);
```

## Begründung

- **URL + note + file** macht Tests deterministisch: `note` und `file` sind ohne Netzwerk-Zugriff. Production-Scouts nutzen `url`.
- **PID-File-Lock** ist Posix- und Windows-portabel und ueberlebt Crashes. DB-Tabelle ist nur Audit.
- **Hybrid-Frequenz** schuetzt vor zu schnellem Re-Run, ohne den Scheduled-Task aufwendig konfigurieren zu muessen.
- **Voller Run pro Trigger** ist einfacher als inkrementell und passt zu max-20-Quellen-Limits.
- **Quarantaene weicht nicht ab** vom M2-Pattern.

## Konsequenzen

### Positiv

- Reuse der bestehenden capture/extract/ingest-Pipeline.
- Klare Audit-Spur via `scout_runs` + Markdown-Log.
- Test-friendly: Mock-Provider plus `note`-Quellen erlauben deterministische Tests.
- Pilotbereich kann mit einem File ergaenzt werden.

### Negativ

- Andreas muss den Scheduled-Task selbst einrichten (Plattform-spezifisch).
- Bei vielen Quellen pro Scout kann ein Run mehrere Minuten dauern; das ist OK fuer M7.
- Lock-File auf Windows-Netzwerk-Share verhaelt sich subtil anders — aktuell nur lokal, also unkritisch.

### Risiken und Mitigationen

| Risiko | Mitigation |
|---|---|
| LLM-Halluzination beim Update | Update-Proposals durchlaufen normalen Review-Workflow |
| Quelle aendert sich silent (nur Whitespace) | Hash-Vergleich auf normalisiertem Inhalt (siehe `sources.hashing`) |
| Doppellauf bei manuellem + Scheduled-Trigger | Lock-File mit Stale-Detection |
| Scout-Liste laeuft aus dem Ruder | `max_sources_per_run`-Hard-Limit, Default 20 |
| Source-URL-Drift | Scout-Definition versioniert in Git, Cleanup ueber neuen Commit |

## Bewusst nicht enthalten

- Update-Scout auf VPS (M6 ist read-only).
- Mehrere Scouts parallel pro Trigger (kann ueber Scheduled-Tasks gestaffelt werden).
- Web-UI fuer Scout-Steuerung (kann in Phase F kommen).
- Auto-Approve von Update-Proposals (Andreas reviewed weiterhin manuell).

## Verweise

- [ADR-0003](ADR-0003-agent-proposals-not-direct-writes.md) — Agent-Proposals
- [ADR-0006](ADR-0006-source-policy-and-copyright-boundaries.md) — Source-Policy
- [ADR-0010](ADR-0010-llm-client-wrapper-implementation.md) — Quarantaene-Pattern
- [ROADMAP.md](../ROADMAP.md) — M7
