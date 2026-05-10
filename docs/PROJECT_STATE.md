# Project State

**Stand:** 2026-05-10
**Aktive Tranche:** M7 — First Update Scout (abgeschlossen, Push ausstehend)
**Aktuelle Version:** 0.8.0-first-update-scout (in Vorbereitung)
**Repository:** https://github.com/andreaskeis77/curio

Dieses Dokument ist die **lebende Statusübersicht** des Projekts. Es wird nach jeder relevanten Tranche aktualisiert.

---

## Was gerade gilt

- **Phase:** M7 abgeschlossen. Der MVP-Scope der ROADMAP ist damit komplett — alle 8 Kern-Tranchen (T0.1 + M1–M7) sind erledigt; lediglich das physische VPS-Setup (M6) und der Restore-Drill stehen noch bei Andreas an.
- **Was es schon gibt:** Repo, kanonische Dokumente, ADRs 0001–0019, ROADMAP, Konzepte, vollständige CLI mit `registry`, `capture`, `sources`, `extract`, `ingest`, `proposal`, `quarantine`, `pages`, `lint`, `search`, `index rebuild`, `browse`, `questions list`, `freshness`, `eval golden`, `readmodels rebuild|status`, `web run`, `bundle build`, **`scout list|show|run`**. SQLite v5 mit 17 Tabellen (15 + `pages_fts` + `scout_runs`). FastAPI-Backend inkl. **`/api/scouts`** und **`/healthz/deep`**. Read-Models inkl. `freshness_dashboard.scouts`-Section. PowerShell-Skripte für Bundle/Deploy/Backup/Restore/Off-Site. Pilot-Scout `scouts/unesco-welterbe.yaml`.
- **Was es noch nicht gibt:** Live-VPS-Deployment (Andreas-Aktion aus M6), Embeddings/Hybrid Retrieval (Phase E), erweiterte Mobile/PWA-Features (Phase F).
- **LLM-Modus:** Mock-Default. Anthropic/OpenAI implementiert.
- **Pilotbereiche im Fokus:** UNESCO (mit Pilot-Scout), Pacojet (Fixtures vorhanden).

## Letzte abgeschlossene Tranche

**M7 — First Update Scout**

Deliverables:

- **ADR-0019** Update-Scout-Modell. URL+note+file als Quellen-Typen, PID-File-Lock mit Stale-Detection (1h), hybride Frequenz (`frequency_hours` aus YAML, `force=True` als Override), `scout_runs`-Audit-Tabelle, Markdown-Run-Logs, Quarantäne-Reuse aus M2.
- **Schema-Migration 0005** (`scout_runs`-Tabelle). REQUIRED_TABLES um `scout_runs` ergänzt.
- **`scouts/`-Modul**: Pydantic-Schema (extra=forbid, lower-kebab-id), YAML-Loader mit Filename↔id-Konsistenzcheck, PID-File-Lock (`O_CREAT|O_EXCL`, Stale-Detection per Timestamp + tote PID), Runner mit Lock-Akquise, Frequenz-Check, Source-Iteration, Outcome-Tracking, atomic Run-Log-Write.
- **`scouts/unesco-welterbe.yaml`**: Pilot-Scout mit zwei `note`-Quellen (deterministisch testbar, ohne Netzwerk).
- **CLI**: `curiosity scout list|show|run` mit `--force/--dry-run`-Optionen, Rich-Tabelle für Run-Output.
- **JSON-API**: `GET /api/scouts` (Liste mit `last_run`-Stempel) und `GET /api/scouts/{id}` (Definition + `recent_runs` LIMIT 20).
- **`freshness_dashboard.json`** erweitert um `scouts: [...]`-Section mit dem letzten completed/skipped/failed-Lauf pro Scout.
- **Goldens** ergänzt um `gq_scouts_discoverable` (jetzt 11 strukturelle Goldens).
- **RUNBOOK**: §"Ab M7" mit Scout-CLI-Befehlen und Beispiel für Windows-Scheduled-Task.
- **Tests (25 neu, total 286)**: `test_scouts_loader.py` (10), `test_scouts_runner.py` (10), `test_scouts_api.py` (5). Schema-Validation, Filename-id-Mismatch, full run capture-to-proposal, dry-run, Frequenz-Skip, Force-Override, Lock-blocks-parallel, Stale-Lock, Idempotenz mit DuplicateSourceError, API-Detail/recent_runs, freshness_dashboard scouts-Section.

Akzeptanzkriterien M7 (alle erfüllt):

- Scout schreibt Proposals, nicht direkt nach Wiki ✓ (Update-Proposals durchlaufen den M3-Review-Workflow).
- Wiki wird nicht automatisch überschrieben ✓ (Scout ruft nur capture/extract/ingest, kein Publish).
- Freshness-Dashboard zeigt Status pro Quelle ✓ (`scouts`-Section mit letztem Lauf je `scout_id`).
- Scout-Ausfall blockiert das System nicht ✓ (Errors landen in `scout_runs.status='failed'`, Lock wird im finally freigegeben).

## Aktive Tranche

Keine. Der ROADMAP-MVP ist komplett. Mögliche Folgepfade: **M6-VPS-Setup live ziehen**, oder **Phase A (Robustheit)**, oder **Pilot-Content publizieren** (UNESCO/Pacojet aus den vorhandenen Fixtures).

## Offene rote Pfade

- VPS-Live-Deployment + Restore-Drill (aus M6) liegen weiterhin bei Andreas.

## Bekannte Einschränkungen

- Update-Scouts laufen nur lokal auf Andreas-Laptop, nicht auf der VPS (read-only-Strategie aus ADR-0004/0017).
- Scout-Quellen mit `type: url` machen echtes HTTP — für Tests werden `note`-Quellen genutzt. Erste Live-URLs werden ergänzt, wenn die UNESCO-Listen-Endpunkte stabil bekannt sind.
- Keine Auto-Trigger für `readmodels rebuild` nach Scout-Run; Andreas muss nach einem Lauf bewusst rebauen, sonst ist `freshness_dashboard.scouts` veraltet (nur API-`/api/scouts` ist immer live).
- `_last_run_at` filtert auf `completed/skipped`. Ein `failed`-Run setzt die Frequenz-Schranke nicht zurück — bewusster Trade-off, sonst würde ein Crash zu rapidem Re-Try führen. Bei Bedarf `scout run --force` nutzen.
- Lock-File-Mechanik ist Posix+Windows-portabel, aber auf Netzwerk-Shares nicht getestet (lokal: kein Issue).

## Aktuelle Umgebung

| Komponente | Stand |
|---|---|
| Python | 3.11+ (getestet auf 3.12) |
| Lint | ruff 0.5+ — alles grün |
| Test | pytest 8.0+ — 286 Tests grün |
| Plattform | Windows 11 Pro (Dev), Windows-VPS (Ziel, M6) |
| LLM Provider | mock (Default) / anthropic / openai |
| Registry | SQLite v5 (15 Tabellen + `pages_fts` + `scout_runs`) |
| Web UI | FastAPI + Jinja2 + Mobile-First-CSS, lokal über `curiosity web run` |
| Deployment | Bundle-Builder + 4 PS-Skripte + 2 WinSW-Configs |
| Scouts | YAML-konfiguriert, lokal lauffähig, Audit in `scout_runs` |
| Dependencies | fastapi, jinja2, uvicorn, markdown-it-py, pydantic, plus die bestehenden |

## Nächste mögliche Tranchen

Der MVP-Scope ist abgeschlossen. Optionen aus der ROADMAP:

- **VPS-Setup durchziehen** (verbleibender Teil von M6: Tailscale, Cloudflare-Tunnel, WinSW-Service-Install, erstes Live-Deploy, Restore-Drill).
- **Phase A — Robustheit**: Registry-Rebuild aus Markdown, mehr Lint-Regeln (Ziel 25+), Backup/Restore als CI-Job, bessere Proposal-Diffs.
- **Phase B — Produkttests und Freshness**: Product-Research-Templates, weitere Update-Scouts.
- **Phase C — Haute Couture**: Personen-/Marken-/Begriffsseiten, Zeitachsen, Essay-/Dossier-Seiten.
- **Phase D — Motorsport / ESC / James Bond**: strukturierte Datenimporte, Jahrgangsseiten.
- **Phase E — Hybrid Search und Query Agent**: Embeddings, Hybrid Retrieval, Source-aware Answers.
- **Phase F — Mobile Polish / PWA**: Offline-Lesen, „Später lesen", Lesefortschritt.
- **Pilot-Content publizieren**: UNESCO/Pacojet aus Fixtures durchlaufen lassen.

## Zuletzt aktualisiert

- 2026-05-08 — initial (T0.1 abgeschlossen).
- 2026-05-08 — M1 Registry Spine abgeschlossen.
- 2026-05-09 — M2 Extraction & Proposal Ingest abgeschlossen.
- 2026-05-09 — M3 Review & Publish abgeschlossen.
- 2026-05-09 — M4 Browse, Search, Lint abgeschlossen.
- 2026-05-09 — M5 Local Web UI abgeschlossen.
- 2026-05-09 — M6 VPS Read-only Preview (Code-Seite) abgeschlossen.
- 2026-05-10 — M7 First Update Scout abgeschlossen.

## Wie dieses Dokument zu pflegen ist

Nach jeder abgeschlossenen Tranche: „Letzte abgeschlossene Tranche" aktualisieren, „Aktive Tranche" auf nächste Phase setzen, Quality Gates verifizieren, ARD/ADR/RUNBOOK bei Architekturwirkung aktualisieren, Datum erweitern.
