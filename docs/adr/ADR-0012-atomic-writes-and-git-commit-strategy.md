# ADR-0012: Atomic Writes und Git-Commit-Strategie

- **Status:** Accepted
- **Datum:** 2026-05-09
- **Tranche:** M3 — Review & Publish

## Kontext

Beim Approval eines Proposals werden mehrere Artefakte gleichzeitig erzeugt oder geändert:

- Eine oder mehrere `wiki/<type>/<slug>.md`-Dateien.
- Ein oder mehrere Source Pages unter `wiki/sources/<source_id>.md`.
- Registry-Updates (`pages`, `page_sources`, `claims`, `proposals.status`).
- Optional: Git-Commit, der diese Änderungen festhält.

Risiken bei naiver Implementierung:

- Ein Crash mitten im Schreiben hinterlässt halbe Markdown-Dateien.
- Registry und Filesystem driften auseinander.
- Ein Git-Commit enthält uneindeutige Mengen an Änderungen.
- Nachträgliche Reproduktion ist schwer.

## Entscheidung

### Atomic File Write

Jede Datei in `wiki/`, `extracted/`, `read_models/` wird in drei Schritten geschrieben:

1. **Write** in `<path>.tmp`.
2. **Validate** Inhalt (Frontmatter-Schema, mindestens parsbar).
3. **Atomic rename** `<path>.tmp` → `<path>` via `Path.replace`.

Bei Fehler in Schritt 1 oder 2: temp-Datei löschen, alte Datei bleibt unangetastet, Exception propagiert.

### Two-Phase Publish

Eine Approval läuft in zwei klar getrennten Phasen:

**Phase A — Build (kein persistenter Side Effect):**

- Lade Proposal aus `proposals/<run_id>/proposal.yaml`.
- Erzeuge In-Memory-Page-Objekte aus `IngestProposalV1.new_pages`.
- Validiere alle Frontmatter-Schemas.
- Berechne Slugs und Pfade — prüfe Kollision mit existierenden Seiten.
- Wenn Kollision oder Schema-Fehler: Abbruch ohne jeglichen Schreibvorgang.

**Phase B — Persist (atomic, mit best-effort Rollback):**

1. Schreibe alle Wiki-Markdown-Dateien (atomic, einzeln).
2. Schreibe Source Page (atomic).
3. Registry-Transaktion: pages, page_sources, claims, proposals.status.
4. Optional: Git-Commit.

Wenn Schritt 3 (Registry) fehlschlägt, werden die in Schritt 1+2 geschriebenen Files **nicht** automatisch entfernt — sie sind gültiges Markdown und können beim nächsten Lauf via `pages`-Rebuild wieder erfasst werden. Inkonsistenz wird als Lint-Warning gemeldet.

### Git-Commit-Strategie

Per Default-Konfiguration wird **nicht** automatisch comitted (`CURIOSITY_PUBLISH_AUTO_COMMIT=false`). Begründung:

- Andreas reviewt Diffs sowieso vor jedem manuellen Commit.
- Auto-Commits können einen verschmutzten Working Tree mit anderen In-Progress-Änderungen vermischen.
- Repos mit gepushten Tags brauchen bewusste Commit-Kontrolle.

Wenn `CURIOSITY_PUBLISH_AUTO_COMMIT=true`:

- Nur die Dateien des aktuellen Publish werden gestaged (nicht `git add -A`).
- Commit-Message folgt Convention:
  ```text
  publish: <proposal_id> -> N pages from src_<source_id>

  - wiki/places/alhambra.md (new, type=place)
  - wiki/topics/unesco-welterbe.md (updated)
  - wiki/sources/src_20260509_....md (new)

  Proposal: prop_...
  Source:   src_...
  Run:      run_...
  ```
- Vor Commit: Pre-Check, dass `git status` außer den publish-bezogenen Dateien sauber ist; sonst Abbruch des Auto-Commits (Publish selbst läuft trotzdem durch, Andreas committet manuell).

### Reject / Request-Changes

- `reject`: Setzt `proposals.status = 'rejected'`. Keine Wiki-Dateien werden erzeugt. Proposal-Ordner bleibt als Audit-Trail.
- `request-changes`: Setzt `proposals.status = 'needs_changes'`. Keine Wiki-Dateien. Notiz im Proposal-Ordner als `review_notes.md`.

## Begründung

- **Atomic Rename** ist auf POSIX und Windows-NTFS atomisch genug für unsere Zwecke.
- **Two-Phase Publish** verhindert teilweise Schreibvorgänge bei Kollisions-Erkennung früh.
- **Best-effort Rollback** ist pragmatischer als verteilte Transaktionen — Markdown-Dateien sind regenerierbar und Lint findet Drift.
- **Default kein Auto-Commit** erfüllt das Working-Agreement-Prinzip „bei Git-Operationen vorher fragen".
- **Saubere Commit-Convention** macht Git-Historie reviewbar.

## Konsequenzen

### Positiv

- Keine halben Wiki-Seiten.
- Klare Auditierbarkeit pro Proposal.
- Reject und Request-Changes sind ohne Wiki-Schaden möglich.
- Andreas behält Git-Kontrolle.

### Negativ

- Best-effort Rollback ist nicht perfekt — Drift muss durch Lint erkannt werden.
- Validation in Phase A erfordert vollständige Frontmatter-Templates vor Publish.

### Risiken und Mitigationen

| Risiko | Mitigation |
|---|---|
| Slug-Kollision mit existierender Page | Phase-A-Check; bei Kollision Abbruch und Hinweis auf existierende Page |
| Registry-Insert-Fail nach File-Write | Lint-Warning, `registry rebuild-from-markdown` (kommt später) |
| Auto-Commit verschmutzt Working Tree | Pre-Check, dass nur Publish-Files staged werden |
| Atomic rename schlägt unter Windows fehl bei laufendem Lock | Retry mit kurzer Pause; bei dauerhaftem Fehler Exception |

## Verweise

- [ADR-0001](ADR-0001-markdown-plus-sqlite-registry.md) — Markdown + SQLite
- [ADR-0003](ADR-0003-agent-proposals-not-direct-writes.md) — Proposal-Pattern
- [SECURITY.md](../SECURITY.md) — Pre-Push-Checkliste
- [ROADMAP.md](../ROADMAP.md) — M3
