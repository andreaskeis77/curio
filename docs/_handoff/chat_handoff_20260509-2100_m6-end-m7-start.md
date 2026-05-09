# Chat Handoff — M6 Ende / M7 Start (First Update Scout)

**Erstellt:** 2026-05-09
**Letzte abgeschlossene Tranche:** M6 — VPS Read-only Preview (Code-Seite, `v0.7.0-vps-read-only-preview` Tag in Vorbereitung)
**Nächste Tranche:** M7 — First Update Scout
**Repo:** https://github.com/andreaskeis77/curio

---

## Zustand am Ende dieser Session

- 261 pytest-Tests grün, alle 4 Quality Gates grün.
- Working Tree sauber bis auf den letzten M6d-Commit.
- ADRs 0001–0018. ADR-0017 dokumentiert VPS-Deployment-Modell, ADR-0018 Backup/Restore.
- Web-UI weiterhin lokal lauffähig (`curiosity web run`).
- Bundle-Builder (`curiosity bundle build`) baut Deployment-ZIPs nach `dist/`.
- `/healthz/deep` liefert strukturierten Status für Smoke-Tests.
- 4 PowerShell-Skripte unter `scripts/` (deploy/backup/restore/pull-vps-backups).
- 2 WinSW-XMLs unter `scripts/winsw/`.

## VPS-Setup-Schritte, die Andreas selbst macht (nicht in dieser Session)

ADR-0017 listet sie, RUNBOOK §"VPS-Deployment-Prozedur (M6)" hat die Detail-Schritte. Kurz:

1. **Tailscale** auf VPS installieren, Andreas-Laptop autorisieren, Tailnet-Hostname `vps-curiosity` setzen.
2. **Windows-Firewall**: RDP nur fuer Tailscale-Subnetz, sonst nichts inbound.
3. **Python 3.12** auf VPS installieren.
4. **Verzeichnisse anlegen**: `c:\curiosity\app\`, `c:\curiosity\service\`, `c:\curiosity\logs\`, `c:\curiosity\backups\`.
5. **WinSW-x64.exe** beziehen, beide XMLs aus `scripts/winsw/` kopieren, Services installieren und starten.
6. **Cloudflared** installieren, Tunnel im CF-Dashboard anlegen, Token in System-ENV `CLOUDFLARE_TUNNEL_TOKEN`, DNS auf den Tunnel zeigen lassen.
7. **Backup-Scheduled-Task** für `scripts/backup-windows-vps.ps1 -Reason daily` (taeglich 03:00).
8. **Erstes Bundle bauen** (lokal) und deployen.
9. **Restore-Drill**: einmal vor Live-Schaltung, danach quartalsweise.

Erst danach gilt M6 als end-to-end abgeschlossen. Bis dahin: Code/Skripte/Doku sind fertig, Live-VPS-Verifikation ist die Aufgabe.

## Was nicht im PROJECT_STATE steht (Notizen für die nächste Session)

### 1. CLI fuer Deploy-Trigger

`curiosity bundle build` baut, aber das Hochladen + Trigger des Deploy-Skripts ist manuell. Wenn das oft genug stoert, ein `curiosity bundle deploy --vps-host vps-curiosity` ergaenzen, das per `Copy-Item` + `Invoke-Command` ueber WinRM/SSH ausloest. Nicht in M6 — kommt wenn Andreas es braucht.

### 2. Bundle ist nicht signiert

ADR-0017 hat das bewusst weggelassen, weil VPS und Laptop gegenseitig vertraulich sind und Tailscale die Linie absichert. Wenn Cloud-Distribution kommt (z.B. fuer einen zweiten User), braucht es minisign/age-Signaturen — eigenes ADR.

### 3. cloudflared-Token-Pflege

Der Token steht in der System-ENV der VPS. Beim Rotation: einfach `setx CLOUDFLARE_TUNNEL_TOKEN <neu> /M` als Admin und Service neu starten. Nicht ins Repo committen.

### 4. Restore-Drill mit eigenem Service-Namen

`scripts/restore-windows-vps.ps1 -ServiceName curiosity-web-drill -AppRoot c:\curiosity\drill -HealthPort 8766` erlaubt parallele Drill-Instanz, ohne den echten Service zu stoeren. Der Drill braucht aber eine zweite WinSW-Installation mit dem `-drill`-Suffix — RUNBOOK haelt das aktuell nur als Pattern, nicht mit fertiger XML.

### 5. /healthz/deep ist tolerant

Wiki-Verzeichnis fehlend → `degraded`, nicht `down`. Das ist gewollt: die UI antwortet auch ohne Pages. Pre-Deploy-Smoke verlangt nur `ok|degraded`. Nach `bundle build` + `deploy` sollte `ok` rauskommen.

### 6. Tests + Sandbox

Bundle-Tests laufen vollstaendig in tmp_path; sie schreiben kein ZIP nach `dist/`. Quality Gates laufen auf der Dev-Umgebung; CI ist M6-Scope nicht.

### 7. CLI-Help-String pflegen

Top-Level-Help und `info`-Footer sind auf "M6 VPS Read-only Preview". M7 entsprechend aktualisieren.

## M7 Scope (aus ROADMAP.md)

**Ziel:** Kontrollierte Aktualitätslogik für genau einen Bereich.

### Deliverables

- Scout-Definition als YAML (`scouts/<name>.yaml`): erlaubte Quellen, Frequenz, Output-Format.
- Scheduler (lokal, **nicht** auf VPS!) via Scheduled Task / Skript-Wrapper.
- Update-Proposal-Erzeugung statt Direkt-Aenderung — der Scout produziert ein normales Proposal, das Andreas review-en muss.
- Freshness-Dashboard erweitert: Status pro Bereich (`docs/_ops/scout_runs/`).
- Quarantaene bei Unsicherheit (Reuse von M2-Pattern).
- Scout-Logs in `docs/_ops/scout_runs/<run_id>.md`.
- ADR-0019 Update-Scout-Modell.

**Empfohlener erster Scout:** UNESCO-Welterbe oder eine kleine Produktkategorie (z.B. Powerbanks). Nicht beide gleichzeitig.

### Akzeptanzkriterien

- Scout schreibt Proposals, nicht direkt nach Wiki.
- Wiki wird nicht automatisch ueberschrieben.
- Freshness-Dashboard zeigt Status pro Quelle.
- Scout-Ausfall blockiert das System nicht.

### Bewusst nicht in M7

- Scout auf VPS (M7 laeuft auf Andreas-Laptop).
- Mehrere Scouts parallel.
- Web-UI fuer Scout-Steuerung.

## Tipps für die Umsetzung

1. **Scout ist im Kern eine `capture` + `extract` + `ingest`-Sequenz** mit YAML-Konfiguration und Frequenz. Reuse der bestehenden `capture_url`/`extract_source`/`ingest_source`-Funktionen.

2. **YAML-Schema** fuer Scouts klein halten: `id`, `domain`, `sources` (Liste von URL-Templates oder Listen-URLs), `prompt_id`, `frequency_hours`, `dry_run` (default true). Dry-Run baut nur die Source-Liste, ohne capture.

3. **Scheduler**: simpler `curiosity scout run <id>` CLI-Befehl, getriggert per Windows-Scheduled-Task. Skript-Wrapper `scripts/run-scout.ps1` mit Logging und Lock-File (kein Doppellauf).

4. **Quarantaene**: bei Schema-Drift, Prompt-Injection, oder wenn URL-Liste leer ist. Direkt in vorhandene `quarantine_cases`-Tabelle schreiben.

5. **Freshness-Dashboard erweitern**: pro Domain einen letzten Scout-Lauf, Anzahl produzierter Proposals, Anzahl `quarantined`. Read-Model `freshness_dashboard.json` um `scouts`-Feld erweitern.

6. **Tests**: Scout-Run mit Mock-Provider und 1-2 Fixture-URLs, prueft dass Proposals erzeugt werden und kein Direktwrite nach `wiki/`.

## Nicht-vergessen-Liste

- [ ] ADR-0009 README-Eintrag fuer ADR-0019 ergaenzen.
- [ ] PROJECT_STATE.md auf M7-Scope aktualisieren wenn fertig.
- [ ] Quality Gates komplett gruen.
- [ ] Goldens fuer Scout-Funktion (mind. 1 strukturell).
- [ ] Tag `v0.8.0-first-update-scout`.
- [ ] Diesen Handoff bei Bedarf als „abgeschlossen" markieren.

## Quick-Recovery für Cold Start

```powershell
cd c:\projekte\curio
.\.venv\Scripts\Activate.ps1
python -m curiosity_wiki info        # zeigt Phase, Schema-Version, Source-Count
python -m pytest -q                  # erwartet: 261 passed
python tools\run_quality_gates.py    # erwartet: 4/4 OK
git log --oneline -8                 # erwartet: M6d-Commit zuoberst
git tag                              # erwartet: v0.7.0-vps-read-only-preview
python -m curiosity_wiki bundle build --git-sha (git rev-parse HEAD)
```

Falls etwas anders: PROJECT_STATE.md prueft den wahren Stand.
