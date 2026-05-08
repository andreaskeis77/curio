# Validation Protocol

**Status:** v0.1 — Verbindlich
**Stand:** 2026-05-08

Validierung ist eine **Leiter**, kein Sack voller Checks. Reihenfolge zählt: was unten brennt, kann oben grün wirken.

---

## Die 10 Stufen

### Stufe 1 — Repo-/Pfad-Sanity

**Frage:** Stimmt der Working Tree mit der Erwartung überein?

```powershell
git status --short
git log --oneline -5
```

**Prüfungen:**

- Keine Runtime-Artefakte versehentlich tracked.
- Keine privaten Raw-Dateien im falschen Bereich.
- Keine `.env` / Secrets im Diff.
- Keine ungewollten Binärdateien.

### Stufe 2 — Import-/CLI-Gate

**Frage:** Ist der Code überhaupt importierbar und ausführbar?

```powershell
python -c "import curiosity_wiki; print(curiosity_wiki.__version__)"
python -m curiosity_wiki --help
```

**Prüfungen:**

- Paket importiert ohne Errors.
- CLI startet und zeigt Hilfe.
- Erwartete Top-Level-Commands sind registriert.

### Stufe 3 — Schema-/Registry-Gate

**Frage:** Ist die Datenstruktur konsistent?

**Ab M1:**

```powershell
python -m curiosity_wiki registry check
```

**Prüfungen:**

- SQLite-Schema vorhanden.
- Migrationen aktuell.
- Fresh State funktioniert (leere Registry initialisierbar).
- Evolved State funktioniert (vorhandene Registry öffnet ohne Korruption).

### Stufe 4 — Letzter grüner Pfad

**Frage:** Funktioniert der letzte erfolgreiche Pfad noch?

**Beispiel:**

- Letzter erfolgreicher Capture-Lauf wird wiederholt.
- Letzte erfolgreiche Lint-Run wird neu ausgeführt.
- Letztes erfolgreiches Proposal wird neu generiert (mit Mock-LLM).

**Prüfung:** Kein Regress in bisher funktionierenden Operationen.

### Stufe 5 — Neuer Pfad

**Frage:** Funktioniert die neu hinzugefügte Funktion?

**Beispiel:**

- Neue CLI-Command wird im Dry Run getestet.
- Neue Lint-Regel wird gegen Fixture getestet.
- Neuer API-Endpunkt wird mit Beispiel-Request getestet.

**Prüfung:** Erwarteter Output, keine Side Effects, idempotent.

### Stufe 6 — Wiki-Integrity-Gate

**Frage:** Ist das Wiki konsistent?

**Ab M3:**

```powershell
python -m curiosity_wiki lint
```

**Prüfungen:**

- Frontmatter vollständig (id, type, status, freshness, sources).
- Wikilinks auflösbar.
- Quellen referenziert.
- Claims an Sources gebunden (für harte Fakten).
- Keine Duplicate Titles.
- Keine orphan pages (außer absichtlich).
- Volatile Pages mit `last_checked` und `review_after`.

### Stufe 7 — LLM-Fidelity-Gate

**Frage:** Macht der LLM, was er soll — und nicht, was er nicht soll?

**Ab M2:**

```powershell
python -m curiosity_wiki eval golden
```

**Prüfungen:**

- Fixture-Quelle → erwartete Proposal-Struktur.
- Keine erfundenen Fakten in kontrollierten Testfällen.
- Unsicherheiten markiert.
- Quellenbindung vorhanden.
- Riskante Quelle quarantiniert (Prompt Injection Fixture).
- Keine direkte Wiki-Mutation.

### Stufe 8 — UI-Smoke

**Frage:** Lädt die UI, und sind die wichtigsten Views renderbar?

**Ab M5:**

```powershell
python -m curiosity_wiki web start --check-only
curl http://127.0.0.1:8765/api/health
```

**Prüfungen:**

- Home lädt.
- Beispielseite (UNESCO, Pacojet) lädt.
- Suche/Browse lädt.
- Mobile Layout rudimentär geprüft (DevTools Responsive Mode).

### Stufe 9 — Ops-/Backup-Gate

**Frage:** Wenn jetzt etwas crasht, ist es wiederherstellbar?

**Ab M6:**

```powershell
.\scripts\backup.ps1
.\scripts\restore.ps1 --dry-run --target tmp\restore-test
```

**Prüfungen:**

- Registry-Backup transaktionssicher.
- Raw/Wiki-Backup vollständig.
- Restore-Probe auf leerem Verzeichnis erfolgreich.
- Read Models rebuildbar.

### Stufe 10 — Release Evidence

**Frage:** Ist der Stand dokumentiert und nachvollziehbar?

**Prüfungen:**

- Gate-Logs gespeichert in `docs/_ops/quality_gates/`.
- Doku aktualisiert (PROJECT_STATE).
- Bei Architekturwirkung: ARD/ADR aktualisiert.
- Handoff aktualisiert.
- Tag oder Release-Notiz erstellt (bei Release-Tranche).

---

## Wann welche Stufen?

| Tranche-Art | Mindeststufen |
|---|---|
| Doku-only | 1, 2 |
| Code-Refactor ohne Verhalten | 1, 2, 5 (ggf. 4) |
| Schema-Migration | 1, 2, 3, 4, 5 |
| Capture/Extraction | 1, 2, 3, 4, 5 |
| Ingest mit LLM | 1, 2, 3, 5, 7 |
| Wiki-Publish | 1, 2, 3, 6, 5 |
| UI-Änderung | 1, 2, 8 |
| Deployment | 1, 2, 8, 9, 10 |
| Release | alle 10 |

## Fresh State und Evolved State

**Fresh State:** Neues Repo, leere Registry, Beispielquellen.
**Evolved State:** Vorhandene Beispielseiten, alte Source-Snapshots, alte Proposals, ältere Schema-Version.

Tests müssen **beide Modi** kennen.

Beispiele für Evolved-State-Tests:

- Eine alte Wiki-Seite ohne `claim_ids` wird migriert.
- Eine alte Source Page mit früherem Frontmatter bleibt lesbar.
- Ein alter Proposal-Ordner wird nicht kaputtinterpretiert.
- Ein alter Search Index wird rebuildbar gelöscht und neu erzeugt.

## Replay

Jeder Ingest-Run muss replay-bar sein.

Run Evidence speichert:

```yaml
run_id: run_20260507_184512_ab12
source_id: src_20260507_181030_unesco_alhambra
source_snapshot_hash: ...
extractor_version: trafilatura_...
prompt_id: ingest_v0_3
prompt_hash: ...
model: ...
model_parameters:
  temperature: 0
  max_tokens: ...
output_proposal_id: prop_...
created_at: 2026-05-07T18:45:12+02:00
status: completed | failed | quarantined
```

Replay = Source + Snapshot Hash + Prompt + Model + Parameters → derselbe Proposal-Output (Mock) oder semantisch äquivalent (echter LLM).

## Wenn eine Stufe rot ist

- **Stufe 1–3 rot:** Nichts weiter machen. Sofort fixen.
- **Stufe 4 rot:** Regress. Nächste Stufe nicht. Bug fixen.
- **Stufe 5 rot:** Neue Funktion fehlerhaft. Bug fixen vor Stufe 6.
- **Stufe 6–7 rot:** Qualitätsverlust. Documenten in LESSONS_LEARNED, dann fixen.
- **Stufe 8–10 rot:** Release blockiert. Rollback oder Fix vor Push.

## Verweise

- [TEST_STRATEGY.md](TEST_STRATEGY.md) — Testschichten
- [DELIVERY_PROTOCOL.md](DELIVERY_PROTOCOL.md) — Tranchen
- [RUNBOOK.md](RUNBOOK.md) — Betrieb
