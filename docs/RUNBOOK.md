# Runbook

**Status:** v0.1
**Stand:** 2026-05-08

Operativer Leitfaden für Entwicklung und Betrieb.

---

## Schnellstart (Dev-Laptop)

```powershell
# 1. Repo klonen
git clone https://github.com/andreaskeis77/curio.git
cd curio

# 2. Virtuelle Umgebung
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 3. Dependencies
pip install -e .[dev]

# 4. CLI prüfen
python -m curiosity_wiki --help
python -m curiosity_wiki --version
python -m curiosity_wiki paths

# 5. Tests
python -m pytest -q
python -m ruff check src tests tools
```

## Tägliche Befehle

| Zweck | Befehl |
|---|---|
| Tests | `python -m pytest -q` |
| Lint | `python -m ruff check src tests tools` |
| Format-Check | `python -m ruff format --check src tests tools` |
| Format anwenden | `python -m ruff format src tests tools` |
| Quality Gates | `python tools/run_quality_gates.py` |
| Secret Scan | `python tools/secret_scan.py` |
| CLI Help | `python -m curiosity_wiki --help` |
| Pfade prüfen | `python -m curiosity_wiki paths` |

## Befehle pro Phase (geplant)

### Ab M1

```powershell
python -m curiosity_wiki registry init
python -m curiosity_wiki registry check
python -m curiosity_wiki capture url "https://..." --why "..."
python -m curiosity_wiki capture file "C:\path\to\file.pdf" --why "..."
python -m curiosity_wiki capture note "Pacojet Test" --why "..."
python -m curiosity_wiki sources list
python -m curiosity_wiki sources show src_...
```

### Ab M2

```powershell
python -m curiosity_wiki extract <source_id>
python -m curiosity_wiki ingest <source_id>
```

### Ab M3

```powershell
python -m curiosity_wiki proposal list
python -m curiosity_wiki proposal show <id>
python -m curiosity_wiki proposal approve <id>
python -m curiosity_wiki proposal reject <id>
```

### Ab M4

```powershell
python -m curiosity_wiki search "<query>"
python -m curiosity_wiki browse --random
python -m curiosity_wiki browse --topic "UNESCO"
python -m curiosity_wiki lint
python -m curiosity_wiki eval golden
```

### Ab M5

```powershell
python -m curiosity_wiki rebuild-read-models
python -m curiosity_wiki health-check
python -m curiosity_wiki web start
```

## Backup (lokal)

**Ab M3 stabil:**

```powershell
.\scripts\backup.ps1
```

Erzeugt:

```text
backups\<timestamp>\
  repo.bundle               # git bundle create
  raw-blobs.zip             # raw/-Inhalt, falls vorhanden
  curiosity.sqlite          # Registry-Backup
  curiosity.sqlite.sha256
  manifest.txt              # Liste der gesicherten Pfade + Hashes
```

## Restore (lokal)

```powershell
.\scripts\restore.ps1 --source backups\<timestamp> --target tmp\restore-test
```

Im `--dry-run` werden nur Pfade/Hashes geprüft, keine Dateien geschrieben.

**Restore-Drill** (Pflicht vor erstem stabilen Release):

```powershell
.\scripts\restore.ps1 --source backups\<timestamp> --target tmp\restore-test
cd tmp\restore-test
python -m pytest -q tests/test_smoke.py
python -m curiosity_wiki registry check
```

## Fehlerdiagnose

### CLI startet nicht

```powershell
python -c "import curiosity_wiki; print(curiosity_wiki.__file__)"
pip show curiosity-wiki
```

Prüfen:

- Virtual env aktiviert?
- `pip install -e .[dev]` ausgeführt?
- Python-Version >= 3.11?

### Registry-Fehler

```powershell
python -m curiosity_wiki registry check
sqlite3 data/registry/curiosity.sqlite ".schema"
```

Bei Korruption:

```powershell
# Kopie machen
cp data\registry\curiosity.sqlite data\registry\curiosity.broken.sqlite
# Aus Backup wiederherstellen
.\scripts\restore.ps1 --source backups\<latest> --only registry
```

### Wiki-Lint findet Fehler

```powershell
python -m curiosity_wiki lint
```

Reports landen in `docs/_ops/lint_reports/<timestamp>.md`.

### LLM-API-Fehler

- `.env` prüfen (API-Key vorhanden, korrekter Provider).
- Rate-Limit prüfen.
- Mock-Modus aktivieren: `CURIOSITY_LLM_PROVIDER=mock`.

### Push scheitert

```powershell
git pull --rebase origin main
# Konflikte lösen
git status
# Nach Lösung
git rebase --continue
git push
```

## Logs

```text
logs/
  app.log         # allgemein
  jobs.log        # Background-Jobs
  ingest.log      # LLM-Ingest
  deploy.log      # Deployment
  backup.log      # Backups
```

Log-Level via `.env`:

```text
CURIOSITY_LOG_LEVEL=DEBUG
```

## Health (ab M5)

```powershell
curl http://127.0.0.1:8765/api/health
curl http://127.0.0.1:8765/api/health/deep
```

## Windows-VPS (ab M6)

### Deployment

```powershell
.\scripts\deploy-windows-vps.ps1 -Version 0.6.0
```

Schritte:

1. Preflight (Pfade, Disk Space, Service-Status).
2. Backup von Content + Registry.
3. Service stoppen.
4. Release entpacken nach `C:\curiosity\releases\<version>`.
5. `current` Junction aktualisieren.
6. DB-Migration laufen lassen.
7. Read Models rebuilden.
8. Service starten.
9. Healthcheck.
10. Bei Fehler: automatischer Rollback.

### Service-Management

```powershell
# Status
Get-Service CuriosityWiki

# Stop / Start
Stop-Service CuriosityWiki
Start-Service CuriosityWiki

# Logs (in Event Viewer oder)
Get-Content C:\curiosity\logs\app.log -Tail 100 -Wait
```

### Cloudflare Tunnel

- Konfiguriert via `cloudflared.yml`.
- Service `cloudflared` läuft permanent.
- Bei Ausfall: `Restart-Service cloudflared`.

### Tailscale (Admin-Zugang)

- Login: `tailscale up`.
- VPS-IP via Tailscale: `tailscale status`.
- RDP nur über Tailscale-IP.

## Troubleshooting nach Severity

### CRITICAL

- Wiki nicht lesbar.
- Backup zerstört.
- Secret im Repo.

→ Sofort eskalieren, in PROJECT_STATE als roter Pfad markieren, ggf. Rollback.

### MAJOR

- Tests rot.
- Registry inkonsistent.
- LLM-Ingest produziert falsches Schema.

→ Tranche pausieren, Bug-Fix als eigene Tranche.

### MINOR

- Lint-Warnung.
- Veraltete Doku.

→ In nächster Tranche fixen.

## Verweise

- [VALIDATION_PROTOCOL.md](VALIDATION_PROTOCOL.md) — Validierungsleiter
- [SECURITY.md](SECURITY.md) — Sicherheit
- [SOURCE_POLICY.md](SOURCE_POLICY.md) — Quellen
- [RELEASE_PROCESS.md](RELEASE_PROCESS.md) — Releases
