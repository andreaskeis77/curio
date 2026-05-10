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
python -m curiosity_wiki readmodels rebuild
python -m curiosity_wiki readmodels status
python -m curiosity_wiki web run                 # uvicorn auf 127.0.0.1:8765
python -m curiosity_wiki web run --reload        # Dev-Loop
```

### Ab M6

```powershell
# Lokal: Bundle bauen
python -m curiosity_wiki bundle build --git-sha (git rev-parse HEAD)

# Bundle wird nach dist/curiosity-bundle-<sha>-<timestamp>.zip geschrieben.
# Bundle dann via Tailscale-SCP/SMB auf die VPS uebertragen, dort:
#   .\scripts\deploy-windows-vps.ps1 -BundleZip c:\curiosity\incoming\<bundle>.zip
```

### Ab M7

```powershell
# Scouts auflisten und ausfuehren (lokal, NICHT auf VPS).
python -m curiosity_wiki scout list
python -m curiosity_wiki scout show unesco-welterbe
python -m curiosity_wiki scout run unesco-welterbe              # ggf. skipped wegen frequency_hours
python -m curiosity_wiki scout run unesco-welterbe --force      # Frequenz-Schranke umgehen
python -m curiosity_wiki scout run unesco-welterbe --dry-run    # ohne Capture/Ingest

# Scheduled-Task fuer woechentlichen UNESCO-Lauf (Andreas-Laptop):
schtasks /Create /TN "Curiosity Scout UNESCO" /SC WEEKLY /D MON /ST 06:00 ^
    /TR "powershell -NoProfile -Command \"cd c:\projekte\curio; .\.venv\Scripts\Activate.ps1; python -m curiosity_wiki scout run unesco-welterbe\""
```

## VPS-Deployment-Prozedur (M6)

**Erstmaliges Setup auf der VPS** (siehe ADR-0017):

1. Tailscale installieren, dem Tailnet beitreten, Andreas-Laptop autorisieren.
2. Windows-Firewall: RDP nur fuer Tailscale-Subnetz erlauben, alle anderen Inbound-Regeln deaktivieren.
3. Python 3.12 installieren.
4. `c:\curiosity\app\` anlegen (leer), `python -m venv c:\curiosity\app\.venv`.
5. WinSW-x64.exe nach `c:\curiosity\service\curiosity-web.exe` kopieren.
6. `scripts\winsw\curiosity-web.xml` als `c:\curiosity\service\curiosity-web.xml`.
7. `c:\curiosity\service\curiosity-web.exe install` und `... start`.
8. Cloudflared installieren, Tunnel anlegen, Token in `CLOUDFLARE_TUNNEL_TOKEN`-System-ENV.
9. `scripts\winsw\cloudflared.xml` als Service installieren.
10. Backup-Scheduled-Task fuer `scripts\backup-windows-vps.ps1 -Reason daily` einrichten (taeglich 03:00).

**Pro Deploy** (von Andreas-Laptop):

### Schritt 1 — Bundle bauen (Laptop)

```powershell
cd c:\projekte\curio
python -m curiosity_wiki readmodels rebuild
python -m curiosity_wiki bundle build --git-sha (git rev-parse HEAD)
$bundle = Get-ChildItem dist\curiosity-bundle-*.zip | Sort-Object LastWriteTime -Descending | Select-Object -First 1
$bundleHash = (Get-FileHash $bundle.FullName -Algorithm SHA256).Hash.ToLower()
"Bundle: $($bundle.Name)`nSHA256: $bundleHash"
```

### Schritt 2 — Bundle auf die VPS schieben

Drei Optionen, **HTTPS-Pull ist Default**, die anderen nur wenn vorher als Convenience eingerichtet:

**Option A (Default, always works) — HTTPS-Pull über Tailscale-IP:**

```powershell
# Auf dem Laptop einen einmaligen Webserver starten:
cd c:\projekte\curio\dist
python -m http.server 8800
# Terminal blockiert — auf der VPS pullen, dann hier Strg+C.
```

```powershell
# Auf der VPS (RDP-Session):
$laptopTs = "<deine-Laptop-Tailscale-IP>"   # z.B. 100.67.145.119, siehe `tailscale status`
$bundleName = "<bundle-dateiname>.zip"
$dest = "C:\curiosity\incoming\$bundleName"
if (-not (Test-Path C:\curiosity\incoming)) { New-Item -ItemType Directory C:\curiosity\incoming | Out-Null }
Invoke-WebRequest -Uri "http://${laptopTs}:8800/$bundleName" -OutFile $dest
(Get-FileHash $dest -Algorithm SHA256).Hash.ToLower()    # muss dem Laptop-Hash entsprechen
```

**Option B — SMB-Adminshare** (nur wenn der Deploy-User in der lokalen `Administrators`-Gruppe ist, sonst „Netzwerkname nicht gefunden"):

```powershell
# Auf dem Laptop:
$cred = Get-Credential -UserName "<vps-user>" -Message "VPS-Passwort"
New-PSDrive -Name VPS -PSProvider FileSystem -Root \\<tailscale-ip>\c$ -Credential $cred
Copy-Item $bundle.FullName VPS:\curiosity\incoming\
Remove-PSDrive VPS
```

**Option C — RDP-Drive-Redirection** (`\\tsclient\C\…`):

`mstsc` **ohne** `/v:` starten → Reiter „Lokale Ressourcen" → „Mehr..." → Haken bei „Laufwerke" → erst dann Computer/User eintragen → Verbinden. Dann auf der VPS:

```powershell
Copy-Item "\\tsclient\C\projekte\curio\dist\<bundle>.zip" C:\curiosity\incoming\
```

Drive-Redirection kann durch RD-Group-Policy blockiert sein — wenn `Get-ChildItem \\tsclient\` leer ist, fall back auf Option A.

### Schritt 3 — Deploy auslösen (VPS, RDP)

```powershell
cd c:\curiosity\app
.\scripts\deploy-windows-vps.ps1 -BundleZip "C:\curiosity\incoming\<bundle>.zip"
```

Das Deploy-Skript erledigt: Bundle-Hash-Verify, Pre-Deploy-Backup, Service-Stop, Copy, `pip install -e .`, `registry init`, `index rebuild`, `readmodels rebuild`, Service-Start, `/healthz/deep`-Smoke (60s Timeout). Bei Smoke-Fail oder Schritt-Fehler: **Auto-Rollback** aus dem Pre-Deploy-Backup via `restore-windows-vps.ps1`.

Erwartetes Ende: `[deploy] OK`. Bei Browser-Verifikation auf https://wiki.capsule-studio.de/ pruefen, dass die neuen Pages erreichbar sind.

## Backup (VPS)

```powershell
# Manuell (auf der VPS)
.\scripts\backup-windows-vps.ps1                    # daily
.\scripts\backup-windows-vps.ps1 -Reason monthly
```

Backup-Inhalt (siehe ADR-0018): `wiki/`, `read_models/`, `prompts/`, `eval/`, bereinigte `data/registry/curiosity.sqlite`, `pyproject.toml`, `runtime/service.xml`. Manifest mit SHA-256 pro File.

Aufbewahrung:

| Reason | Aufbewahrung |
|---|---|
| daily | 14 Tage |
| pre-deploy | 30 Tage |
| monthly | 12 Monate |

## Restore (VPS)

```powershell
.\scripts\restore-windows-vps.ps1 -BackupZip C:\curiosity\backups\daily\<datei>.zip
```

Schritte: Hash-Verify aus Manifest, Service-Stop, Live-Verzeichnis als Rollback-Snapshot umbenannt, Staging einkopiert, Service-Start, `/healthz/deep`-Smoke. Bei Smoke-Fail Auto-Rollback aus dem Snapshot.

**Restore-Drill** (Pflicht vor Live-Schaltung, danach quartalsweise):

1. Frisches `c:\curiosity\drill\` anlegen.
2. Backup-ZIP nehmen, Restore-Skript mit `-AppRoot c:\curiosity\drill -ServiceName curiosity-web-drill` (paralleler Service auf alternativem Port) ausfuehren.
3. `Invoke-RestMethod http://127.0.0.1:<drill-port>/healthz/deep` → `status: ok`.
4. `c:\curiosity\drill\` aufraeumen.

## Off-Site-Pull (Andreas-Laptop)

```powershell
# Tailscale aktiv vorausgesetzt.
.\scripts\pull-vps-backups.ps1 -VpsHost vps-curiosity -LocalDir c:\curiosity\offsite-backups
```

Skript loescht **nichts**, nur additiver Pull. Calendar-Reminder: alle 1-2 Wochen.

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

## Health (ab M5/M6)

```powershell
# Liveness (ab M5)
curl http://127.0.0.1:8765/healthz

# Anwendungs-API-Health (ab M5)
curl http://127.0.0.1:8765/api/health

# Deep-Health (ab M6) — pruft Registry, FTS5, Wiki-Dir, Read-Models.
curl http://127.0.0.1:8765/healthz/deep
```

`/healthz/deep` liefert `200` mit `status: ok|degraded` oder `503` bei `down`. Wird vom Deploy-Skript als Smoke-Test genutzt.

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
