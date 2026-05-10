# Chat Handoff — M7 Ende / MVP komplett

**Erstellt:** 2026-05-10
**Letzte abgeschlossene Tranche:** M7 — First Update Scout (`v0.8.0-first-update-scout`, Tag in Vorbereitung)
**Nächste Tranche:** offen — Andreas entscheidet (VPS live, Phase A, Phase B, oder Pilot-Content)
**Repo:** https://github.com/andreaskeis77/curio

---

## Zustand am Ende dieser Session

- 286 pytest-Tests grün, alle 4 Quality Gates grün.
- ADRs 0001–0019 (alle MVP-ADRs accepted).
- CLI komplett: registry, capture, sources, extract, ingest, proposal, quarantine, pages, lint, search, index rebuild, browse, questions, freshness, eval golden, readmodels, web run, bundle build, **scout list/show/run**.
- SQLite v5 (Migration 0005 für `scout_runs`).
- FastAPI-API komplett: health, pages, sources, search, browse, proposals, lint, **scouts**, plus `/healthz/deep`.
- Pilot-Scout `scouts/unesco-welterbe.yaml` mit zwei `note`-Quellen.

## MVP-Status

Der ROADMAP-MVP-Scope (T0.1 + M1–M7) ist **vollständig auf der Code-Seite abgeschlossen**. Was noch fehlt:

- **VPS-Setup live** (M6-Restseite): Tailscale, Cloudflare-Tunnel, WinSW-Services, erster Bundle-Deploy, Restore-Drill. Skripte und ADRs liegen vor.
- **Pilot-Content** publizieren: UNESCO und Pacojet aus den Fixtures durch die Pipeline laufen lassen, Pages reviewen und mergen.

Sobald beides durch ist, ist der MVP wirklich live.

## Was nicht im PROJECT_STATE steht (Notizen für die nächste Session)

### 1. Scout-Run-Lock und _last_run_at-Filter

`_last_run_at` filtert auf `status IN ('completed', 'skipped')`. Ein `failed`-Run setzt die Frequenz-Schranke nicht zurück — das ist Absicht, sonst würde ein Crash zu rapidem Re-Try führen. Wenn das in der Praxis stört, einen Lockout-Time-Mechanismus pro `failed` ergänzen.

### 2. Skipped-Run-Refactor im Runner

In M7b-Beta hat der `try`-Block ein early-return im skipped-Pfad gemacht — der `finally`-Block hat dann mit `status="running"` (initial value) überschrieben. Fix: `skipped_run`-Flag, sources-Loop konditional, status-Variable wird durch das `finally` korrekt durchgezogen. Pattern für ähnliche Cases: nie aus `try` returnen, wenn `finally` den finalen DB-Update macht — Flag-Variable nutzen.

### 3. Read-Models-Rebuild nach Scout-Run

Nicht automatisch. Andreas muss nach einem Scout-Lauf manuell `curiosity readmodels rebuild` aufrufen, sonst zeigt die Web-UI veralteten `freshness_dashboard.scouts`-Stand. Die `/api/scouts`-API ist hingegen immer live (liest direkt aus `scout_runs`).

### 4. `note`-Source vs. `url`-Source

Pilot-Scout nutzt `note`-Quellen für deterministische Tests. Echtes URL-Scouting kommt, sobald die Listen-Endpunkte stabil bekannt sind (oder: ein Real-Test mit einer kontrolliert-statischen URL).

### 5. Scheduled-Task

`schtasks`-Befehl steht im RUNBOOK § "Ab M7" als Beispiel. Andreas muss ihn einmal anlegen — der Scout läuft dann wöchentlich. Logs landen in den Windows-Task-Logs plus `docs/_ops/scout_runs/<run_id>.md`.

### 6. Quarantäne wird durchgereicht

Reuse aus M2: `ingest_source` quarantäniert bei Prompt-Injection oder Schema-Drift. Der Scout zählt das nur als `quarantined`-Outcome und läuft mit der nächsten Source weiter — kein Run-Abbruch.

### 7. CLI-Help-String pflegen

Top-Level-Help und `info`-Footer sind auf "M7 First Update Scout". Bei der nächsten Tranche entsprechend ändern.

## Mögliche nächste Tranchen (du entscheidest)

### A) VPS live ziehen

Praxis-Aufgabe; alle Skripte und ADRs sind da. Ziel: M6 vollständig abschließen.

### B) Pilot-Content publizieren

UNESCO + Pacojet aus den Fixtures durch capture → extract → ingest → approve laufen lassen. Erstes echtes Wiki, das man im Browser ansehen kann.

### C) Phase A — Robustheit

Registry-Rebuild aus Markdown, mehr Lint-Regeln (25+ Ziel), CI-Job für Backup/Restore-Tests, bessere Proposal-Diffs.

### D) Phase B — Produkttests

Product-Research-Templates, weitere Update-Scouts (Powerbanks, etc.), Shortlists.

### E) Phase E — Hybrid Search

Embeddings über Wiki-Pages, Hybrid Retrieval, Source-aware Answer-Generation. Hier wird's spannend, aber auch teurer.

## Quick-Recovery für Cold Start

```powershell
cd c:\projekte\curio
.\.venv\Scripts\Activate.ps1
python -m curiosity_wiki info        # zeigt Phase, Schema-Version, Source-Count
python -m pytest -q                  # erwartet: 286 passed
python tools\run_quality_gates.py    # erwartet: 4/4 OK
git log --oneline -10                # erwartet: M7d-Commit zuoberst
git tag                              # erwartet: v0.8.0-first-update-scout
python -m curiosity_wiki scout list  # zeigt unesco-welterbe-Pilot
```

Falls etwas anders: PROJECT_STATE.md zeigt den wahren Stand.
