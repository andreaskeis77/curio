# Project State

**Stand:** 2026-05-09
**Aktive Tranche:** M6 — VPS Read-only Preview (Code-Seite abgeschlossen, VPS-Setup bei Andreas)
**Aktuelle Version:** 0.7.0-vps-read-only-preview (in Vorbereitung)
**Repository:** https://github.com/andreaskeis77/curio

Dieses Dokument ist die **lebende Statusübersicht** des Projekts. Es wird nach jeder relevanten Tranche aktualisiert.

---

## Was gerade gilt

- **Phase:** M6 abgeschlossen auf der Code-/Skript-Seite. ADRs, Bundle-Builder, Deep-Health, alle PowerShell-Skripte (deploy/backup/restore/pull), WinSW-Service-Configs liegen vor und sind getestet. Das eigentliche VPS-Setup (Tailscale, Cloudflare-Tunnel, Service-Installation, Restore-Drill) ist bei Andreas und im RUNBOOK Schritt-für-Schritt dokumentiert.
- **Was es schon gibt:** Repo, kanonische Dokumente, ADRs 0001–0018, ROADMAP, Konzepte, vollständige CLI mit `registry`, `capture`, `sources`, `extract`, `ingest`, `proposal`, `quarantine`, `pages`, `lint`, `search`, `index rebuild`, `browse`, `questions list`, `freshness`, `eval golden`, `readmodels rebuild|status`, `web run`, **`bundle build`**. SQLite v4. Read-Models in `read_models/`. FastAPI-Backend mit allen geplanten Endpunkten, Jinja2-Templates, Mobile-First-CSS. **`/healthz/deep`** für Pre-Deploy-Verifikation. Bundle-Builder mit Whitelist + Sanitierung der DB. PowerShell-Skripte für Backup, Restore, Deploy, Off-Site-Pull. WinSW-XMLs für `curiosity-web` und `cloudflared`.
- **Was es noch nicht gibt:** Live-VPS-Deployment (Andreas-Aktion), Update Scouts, Embeddings/Hybrid Retrieval.
- **LLM-Modus:** Mock-Default. Anthropic/OpenAI implementiert.
- **Pilotbereiche im Fokus:** UNESCO und Pacojet (Fixtures vorhanden, Pipeline vollständig nutzbar bis Web-Reader und Bundle).

## Letzte abgeschlossene Tranche

**M6 — VPS Read-only Preview (Code-Seite)**

Deliverables:

- **ADR-0017** VPS-Deployment-Modell. Cloudflare Tunnel (kein Inbound-Port) + WinSW-Service + ZIP-Bundle + Auto-Migration beim Deploy. Bundle-Whitelist und -Blacklist explizit (keine privaten Sources, keine `raw/`, keine `.env`).
- **ADR-0018** Backup- und Restore-Strategie. Voller VPS-Snapshot in ZIP, daily/pre-deploy/monthly, Aufbewahrung 14d/30d/12mo, Off-Site passiv via Tailscale-Pull, Restore-Drill mit Smoke-Test.
- **`docs/templates/release-notes.md`** als Standard-Skelett.
- **Bundle-Builder** in `src/curiosity_wiki/deploy/`: `build_bundle` mit Whitelist (`wiki/`, `read_models/`, `prompts/`, `eval/`, `src/`, `pyproject.toml`, `README.md`), Blacklist (`raw/`, `proposals/`, `extracted/`, `.env`, `.venv/`, `*.sqlite-wal`/`-shm`, `__pycache__/`, …). SQLite-Sanitierung mit `VACUUM INTO` plus Removal von `access='private'`/`copyright_risk='high'` Sources samt abhängigen Reihen (claims, page_sources, ingest_runs, proposals, quarantine_cases, extractions, source_snapshots). Hash-Manifest mit SHA-256 pro File. Atomic write.
- **CLI** `curiosity bundle build [--out PATH] [--git-sha SHA] [--no-sanitize]` schreibt `dist/curiosity-bundle-<sha>-<timestamp>.zip`.
- **`/healthz/deep`** prüft Registry (Schema-Version), FTS5-Tabelle, Wiki-Verzeichnis, Pages-Count, Read-Models. Status `ok | degraded | down`. 200 bei ok/degraded, 503 bei down.
- **WinSW-Service-Configs** für `curiosity-web` (uvicorn) und `cloudflared` (CF-Tunnel) inkl. Auto-Restart, Log-Rolling, ENV-Pflege.
- **PowerShell-Skripte**:
  - `scripts/backup-windows-vps.ps1 -Reason daily|pre-deploy|monthly`. SQLite via `VACUUM INTO`, Manifest mit SHA-256, Aufbewahrungs-Cleanup, Disk-Space-Preflight.
  - `scripts/restore-windows-vps.ps1 -BackupZip <path>`. Manifest-Hash-Check, Service-Stop, Rollback-Snapshot, Live-Verzeichnis ersetzen, Service-Start, deep-health-Smoke, Auto-Rollback bei Fail.
  - `scripts/deploy-windows-vps.ps1 -BundleZip <path>`. Pre-Deploy-Backup, Bundle-Hash-Verify, Code-Copy, `pip install -e .`, `registry init`, `index rebuild`, `readmodels rebuild`, Service-Start, deep-health-Smoke, Auto-Restore bei Fail.
  - `scripts/pull-vps-backups.ps1` (Andreas-Laptop). Robocopy `/E /XO` ohne `/MIR` von Tailscale-VPS-Share, additiver Pull.
- **Tests (12 neu, total 261)**: `test_bundle.py` (8), `test_health_deep.py` (4). Bundle-Whitelist/Blacklist, private-Sources-Sanitierung, Hash-Match, atomic-no-tmp-residue, deep-health-Statusübergänge.
- **RUNBOOK-Update** mit M5-/M6-Befehlen, VPS-Erst-Setup-Schritten, Deploy-Prozedur, Backup-/Restore-Sektion, Restore-Drill-Anleitung.

Akzeptanzkriterien M6 (Status):

- VPS zeigt read-only Wiki über Cloudflare Tunnel — **offen**, Andreas-Aktion (Skripte + ADR-0017 fertig).
- Service startet automatisch nach Reboot — **vorbereitet** über WinSW-XML.
- Backup wird vor jedem Deploy erzeugt — **automatisch** im `deploy-windows-vps.ps1`.
- Rollback dokumentiert und mindestens einmal getestet — **dokumentiert**, Drill bei Andreas.
- Restore-Drill auf leerem Verzeichnis erfolgreich — **offen**, Andreas-Aktion.
- Keine privaten Raw Sources im Publish-Bundle — **erfüllt** durch Bundle-Whitelist + Sanitierung, durch pytest-Test verifiziert.
- Secret-Scan vor Publish ist grün — **erfüllt** in jedem Quality-Gate-Lauf.

## Aktive Tranche

Keine. Nächste: **M7 — First Update Scout**, sobald die VPS live ist.

## Offene rote Pfade

- VPS-Setup (Tailscale, Cloudflare-Tunnel, Service-Install) und erster Restore-Drill liegen bei Andreas. Solange das nicht durchgelaufen ist, gilt die Phase nicht als end-to-end live.

## Bekannte Einschränkungen

- Mobile-Smoke (M5) per Browser-DevTools wurde nicht automatisiert — Andreas-Test offen.
- Read-Models müssen weiterhin manuell per `readmodels rebuild` gebaut werden (ADR-0016 Default).
- Bundle-Builder kopiert die Live-DB konsistent über `VACUUM INTO`; bei sehr aktiver Schreiblast könnte das einen Connection-Lock verursachen — Mock/Read-only auf der VPS macht das unproblematisch.
- Keine Bundle-Signatur (z.B. minisign) — vertraut wird auf Tailscale + lokalen Hash-Check. Cloud-Verteilung würde Signing erfordern.
- Off-Site-Backups sind unverschlüsselt; Andreas-Laptop und VPS sind beide vertraulich.
- Slug-Kollision blockt Publish weiterhin; ein "update existing page"-Pfad fehlt.

## Aktuelle Umgebung

| Komponente | Stand |
|---|---|
| Python | 3.11+ (getestet auf 3.12) |
| Lint | ruff 0.5+ — alles grün |
| Test | pytest 8.0+ — 261 Tests grün |
| Plattform | Windows 11 Pro (Dev), Windows-VPS (Ziel) |
| LLM Provider | mock (Default) / anthropic / openai |
| Registry | SQLite v4 (15 Tabellen + `pages_fts`) |
| Web UI | FastAPI + Jinja2 + Mobile-First-CSS, lokal über `curiosity web run` |
| Deployment | Bundle-Builder + 4 PS-Skripte + 2 WinSW-Configs |
| Dependencies | fastapi, jinja2, uvicorn, markdown-it-py, plus die bestehenden |

## Nächste Tranche: M7 — First Update Scout

Geplante Deliverables (siehe ROADMAP §M7):

- Scout-Definition als YAML: erlaubte Quellen, Frequenz, Output-Format.
- Scheduler (lokal, nicht auf VPS): Scheduled Task / cron.
- Update-Proposal-Erzeugung statt Direkt-Änderung.
- Freshness-Dashboard erweitert: Status pro Bereich.
- Quarantäne bei Unsicherheit.
- Scout-Logs in `docs/_ops/ingest_runs/`.
- ADR-0019 Update-Scout-Modell.

Empfohlener erster Scout: UNESCO oder eine kleine Produktkategorie. Nicht beide gleichzeitig.

## Zuletzt aktualisiert

- 2026-05-08 — initial (T0.1 abgeschlossen).
- 2026-05-08 — M1 Registry Spine abgeschlossen.
- 2026-05-09 — M2 Extraction & Proposal Ingest abgeschlossen.
- 2026-05-09 — M3 Review & Publish abgeschlossen.
- 2026-05-09 — M4 Browse, Search, Lint abgeschlossen.
- 2026-05-09 — M5 Local Web UI abgeschlossen.
- 2026-05-09 — M6 VPS Read-only Preview (Code-Seite) abgeschlossen.

## Wie dieses Dokument zu pflegen ist

Nach jeder abgeschlossenen Tranche: „Letzte abgeschlossene Tranche" aktualisieren, „Aktive Tranche" auf nächste Phase setzen, Quality Gates verifizieren, ARD/ADR/RUNBOOK bei Architekturwirkung aktualisieren, Datum erweitern.
