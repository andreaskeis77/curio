# Delivery Protocol

**Status:** v0.1 — Verbindlich
**Stand:** 2026-05-08

Wie eine Tranche umgesetzt, geprüft und committed wird. Dieses Protokoll reduziert Friction zwischen Konzept und Code.

---

## Was ist eine Tranche?

Eine Tranche ist eine **abgeschlossene, validierbare Veränderung** mit klarem Scope, Akzeptanzkriterien und Risiko-Bewusstsein. Sie ist **kleiner als ein Release**, aber **größer als ein einzelner Edit**.

Beispiele für Tranche-Granularität:

- ✅ „SQLite-Schema v1 + Migration-Runner + Tests" (eine Tranche).
- ✅ „Capture-CLI für URL und File + Hashing + Duplicate Detection" (eine Tranche).
- ❌ „Capture + Extraction + Ingest + Review" (zu groß — sind 4 Tranchen).
- ❌ „Tippfehler in README" (zu klein — direkter Edit reicht).

## Tranche-Lebenszyklus

```text
1. Tranche-Definition       (was, warum, scope, risk, accept)
        ↓
2. Branch                    (feature/<tranche>)
        ↓
3. Kleine commits             (klar, fokussiert, mit conventional types)
        ↓
4. Tests / Quality Gates      (alle relevanten)
        ↓
5. Diff Review                (git diff lesen, nicht nur fühlen)
        ↓
6. Doku-Update                (PROJECT_STATE, ggf. ARD/ADR/RUNBOOK)
        ↓
7. Merge nach main            (PR oder direkt, je nach Solo-Mode)
        ↓
8. Tag bei Release-Wirkung    (siehe RELEASE_PROCESS.md)
        ↓
9. Handoff-Update              (docs/_handoff/)
        ↓
10. Tranche-Notiz in PROJECT_STATE
```

## Tranche-Definition (Pflichtfelder)

Vor jeder Tranche schreiben wir kurz auf:

```markdown
### Tranche T<x.y> — <Kurzname>

**Ziel:** <ein Satz>
**Scope:**
  - <Datei/Bereich 1>
  - <Datei/Bereich 2>
**Layer betroffen:**
  - [ ] raw
  - [ ] extraction
  - [ ] registry
  - [ ] proposals
  - [ ] wiki
  - [ ] read_models
  - [ ] web_ui
  - [ ] agents
  - [ ] deployment
  - [ ] docs/method
**Risiken:**
  - <Risiko 1>
**Testplan:**
  - <Test 1>
**Doku-Impact:**
  - <Datei 1>
**Akzeptanzkriterien:**
  - <Kriterium 1>
**Bewusst nicht in dieser Tranche:**
  - <Out-of-scope 1>
```

Diese Tranche-Definition kann in PROJECT_STATE, im PR-Body oder im Handoff stehen.

## PR-Template

Auch im Solo-Mode: PRs erzwingen einen kurzen Selbst-Review.

Siehe [.github/pull_request_template.md](../.github/pull_request_template.md).

## Datei-Lieferung

### Erlaubt

- **Vollständige neue Datei** — Write tool, klar.
- **Vollständig ersetzte Datei** — Write tool nach vorigem Read.
- **Begrenzter Edit** — Edit tool mit klarem Old/New.
- **Mehrere Edits in derselben Datei** — wenn alle zur selben logischen Änderung gehören.

### Nicht erlaubt

- Snippet-Patches ohne Kontext.
- Halbfertige Funktionen.
- Auskommentierter Code als Backup.
- TODO-Spam ohne Issue-Verweis.
- Mehrere unzusammenhängende Änderungen in derselben Datei in derselben Tranche.

## Commit-Strategie

### Solo-Mode (default für T0.1–M3)

- `main` ist der Arbeitszweig.
- Trunk-Based Development.
- Kleine, fokussierte Commits.
- Conventional Commit Messages (siehe ENGINEERING_MANIFEST).

### Branch-Mode (ab M4 oder bei Bedarf)

- Feature-Branches wie `feature/m4-search-fts5`.
- Selbst-PR mit Selbst-Review.
- Squash-Merge nach grünen Checks.

### Wann ein neuer Commit, wann amend?

- **Neuer Commit:** Standard. Immer.
- **Amend:** Nur bei sofortigem Tippfehler-Fix vor Push.
- **Niemals:** Amend von gepushten Commits.

## Quality Gates vor Push

Vor jedem Push (auch in `main`):

```powershell
python -m pytest -q
python -m ruff check src tests tools
python -m ruff format --check src tests tools
python tools/run_quality_gates.py
git status --short
```

Wenn **irgendeines** rot ist: kein Push.

## Validierung

Vor dem Tranche-Abschluss läuft die Validierungsleiter aus [VALIDATION_PROTOCOL.md](VALIDATION_PROTOCOL.md).

## Handoffs

Nach jeder relevanten Tranche entsteht ein Handoff:

```text
docs/_handoff/chat_handoff_YYYYMMDD-HHMM_<topic>.md
```

Inhalt:

- Stand am Ende der Tranche.
- Geänderte Dateien.
- Ausgeführte Gates.
- Offene Risiken / rote Pfade.
- Nächste konkrete Tranche.
- Entscheidungen, die in ADR/ARD übernommen wurden.
- Was im nächsten Chat **nicht** neu erklärt werden soll.

Handoffs sind **Übergabe-Artefakte**, nicht Architekturwahrheit.

## Wenn etwas schiefgeht

### Pre-Commit-Hook scheitert

- Investigieren, nicht `--no-verify` benutzen.
- Issue beheben, neuer Commit (kein Amend).

### Test scheitert nach Implementierung

- Tranche bleibt offen.
- Bug-Fix als Teil derselben Tranche.

### Push scheitert (z.B. Konflikt)

- `git pull --rebase` (nicht merge), Konflikte lösen.
- Nicht `--force` außer in eigenem Feature-Branch ohne Co-Author.

### Rollback nötig

- Bei Methodik/Doku: einfacher Revert-Commit.
- Bei Code: Revert-Commit, neue Tranche zur Wieder-Implementierung.
- Bei Daten/Wiki: Backup einspielen, dokumentieren in `docs/_ops/restore_drills/`.

## Verweise

- [ENGINEERING_MANIFEST.md](ENGINEERING_MANIFEST.md)
- [VALIDATION_PROTOCOL.md](VALIDATION_PROTOCOL.md)
- [TEST_STRATEGY.md](TEST_STRATEGY.md)
- [RELEASE_PROCESS.md](RELEASE_PROCESS.md)
