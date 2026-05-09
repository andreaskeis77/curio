# ADR-0017: VPS-Deployment-Modell (Windows, Cloudflare Tunnel, WinSW)

- **Status:** Accepted
- **Datum:** 2026-05-09
- **Tranche:** M6 — VPS Read-only Preview
- **Verwandt:** [ADR-0004](ADR-0004-read-only-vps-first.md) (Read-only-Strategie), [ADR-0006](ADR-0006-source-policy-and-copyright-boundaries.md) (private Quellen)

## Kontext

M6 deployed das Curiosity Wiki erstmals auf einen Windows-VPS — read-only, mit kontrollierbarem Roll-back. Andreas hat einen kleinen Windows-Server (kein Linux). Ziel:

- **Read-only** im Browser (mobil + Desktop) ueber eine oeffentliche URL.
- **Kein offener Inbound-Port** ins Internet — Angriffsflaeche minimieren.
- **Admin-Zugang** nur ueber Mesh-Netz (Tailscale), kein Public-RDP.
- **Auto-Start** des Services nach Reboot.
- **Backup vor Deploy**, dokumentierter Rollback.
- **Keine privaten Raw-Sources** im Public-Bundle (siehe ADR-0006).

Offene Fragen:

1. **Reverse-Proxy:** Caddy auf VPS mit offenem 443, oder Cloudflare Tunnel ohne Inbound-Port?
2. **Service-Wrapper:** WinSW (XML-Config), NSSM (CLI-Config), oder Task-Scheduler?
3. **Bundle-Format:** ZIP, Tarball, oder Git-Bundle?
4. **Bundle-Inhalt:** Welche Files duerfen rueber, welche bleiben lokal?
5. **Schema-Migration auf VPS:** automatisch beim Deploy oder manuell?

## Optionen

### Reverse-Proxy

- **A) Caddy auf VPS, Port 443 offen.** Auto-TLS, klassisches Setup, aber Inbound-Port ist Angriffsflaeche.
- **B) Cloudflare Tunnel.** `cloudflared` baut Outbound-Verbindung zu CF auf, CF terminiert TLS und leitet via Tunnel weiter. Kein Inbound-Port noetig. CF DDOS-Schutz inklusive.
- **C) Nginx.** Ueblich auf Linux, auf Windows umstaendlich.

### Service-Wrapper

- **A) WinSW.** XML-Config, aktiv gepflegt, MSI-frei, kann auch als Single-EXE laufen.
- **B) NSSM.** Aelter, CLI-konfiguriert, weniger Updates.
- **C) Windows-Task-Scheduler.** Funktioniert, aber weniger Service-Semantik (Health-Restart, Logs-Rotation).

### Bundle-Format

- **A) ZIP.** Native Windows, einfach zu handhaben, gut komprimierbar.
- **B) Git-Bundle.** Erlaubt Versionshistorie auf VPS, aber dort wollen wir gar keine History (Snapshot reicht).
- **C) tarball.** Auf Windows umstaendlich.

## Entscheidung

**Cloudflare Tunnel + WinSW + ZIP-Bundle, Migration automatisch beim Deploy.**

### Architektur

```text
Internet
   │
   ▼
[ Cloudflare Edge ]  (TLS-Termination, DDOS, Caching)
   │  Tunnel (Outbound)
   ▼
[ cloudflared.exe ]  (auf VPS, als Service via WinSW)
   │  HTTP 127.0.0.1:8765
   ▼
[ uvicorn → curiosity_wiki.web ]  (auf VPS, als Service via WinSW)
   │
   ▼
[ SQLite + read_models/ + wiki/ ]  (lokal auf VPS)

[ Tailscale ]  ←─ Andreas-Laptop ──── RDP / Skripte
   │  100.x.x.x
   ▼
[ VPS ]  (Tailscale-Member, kein Public-RDP)
```

### Komponenten

- **`cloudflared.exe`** als WinSW-Service. Verbindet sich mit einem konkreten Cloudflare-Tunnel-Token. Rotation per Cloudflare-Dashboard.
- **uvicorn-Service** ueber `python -m curiosity_wiki web run --host 127.0.0.1 --port 8765`. WinSW startet ihn nach Boot, restart-on-failure.
- **Tailscale-Member** auf der VPS. Andreas-Laptop ist im selben Tailnet, RDP geht nur ueber Tailscale-IP, Public-RDP ist Firewall-blockiert.
- **Backup-Scheduled-Task**: taeglich 03:00, schreibt nach `c:\curiosity\backups\<timestamp>.zip` plus Hash-Manifest.

### Bundle-Format

ZIP mit dieser Struktur:

```text
curiosity-bundle-<git_sha>-<timestamp>.zip
├── manifest.json          # version, git_sha, created_at, file_hashes
├── wiki/                  # alle veroeffentlichten Pages und Source-Pages
├── read_models/           # alle Read-Models (Build-Stempel im meta)
├── data/registry/         # SQLite (siehe Whitelist unten)
├── prompts/               # Prompt-Definitionen (versioniert)
├── eval/                  # golden-questions.yaml
└── pyproject.toml         # damit `pip install -e .` auf der VPS klappt
```

**Bundle-Whitelist** (was rein darf):

- `wiki/` — Markdown-Pages aller Typen.
- `read_models/` — generierte JSON/JSONL.
- `prompts/` — Prompt-Registry.
- `eval/` — Goldens.
- `data/registry/curiosity.sqlite` — **bereinigt**: alle Sources mit `access='private'` oder `copyright_risk='high'` werden vor dem ZIP entfernt (siehe ADR-0006).
- `pyproject.toml`, `src/`, `README.md` — fuer das Re-Install-Schritt.

**Bundle-Blacklist** (bleibt lokal):

- `raw/` — alle Raw-Snapshots, ohne Ausnahme.
- `.env`, `*.env*`, `secrets.*`.
- `proposals/` — Pre-Review-Vorschlaege.
- `docs/_ops/` — Quality-Gate-Logs, Lint-Reports, Eval-Reports.
- `extracted/` — Zwischenstand zwischen `raw/` und `proposal`.
- `.venv/`, `__pycache__/`, `data/registry/*.sqlite-wal`, `*.sqlite-shm`.

### Schema-Migration

Beim Deploy wird automatisch `python -m curiosity_wiki registry init` ausgefuehrt. Das ist idempotent — schon angewandte Migrationen werden uebersprungen. Bei Schema-Drift (Bundle hat aelteres Schema als Code) bricht der Deploy ab und wird zurueck gerollt; Andreas muss dann lokal das Bundle neu bauen.

### Deploy-Schrittfolge (siehe `scripts/deploy-windows-vps.ps1`)

1. **Preflight**: Bundle existiert, Hash stimmt, Service ist erreichbar.
2. **Backup** der aktuellen Installation (separates Skript).
3. **Service stoppen** (`Stop-Service curiosity-web`).
4. **Bundle entpacken** in temp, dann `Copy-Item` ueber Live-Verzeichnis (atomar pro File).
5. **`pip install -e .`** im venv, falls `pyproject.toml`-Hash sich geaendert hat.
6. **Registry-Migration**: `curiosity registry init`.
7. **Index-Rebuild**: `curiosity index rebuild`, `curiosity readmodels rebuild`.
8. **Service starten** (`Start-Service curiosity-web`).
9. **Healthcheck**: `curl /healthz/deep`. Falls degraded/down → automatischer Rollback aus dem Backup von Schritt 2.
10. **Cloudflare Tunnel** ist immer up — `cloudflared` braucht keinen Restart, weil sich nur das Backend hinter ihm aendert.

## Begründung

- **Cloudflare Tunnel:** kein offener Port = weniger Angriffsflaeche, CF-Edge-Caching kostenlos, kein Let's-Encrypt-Cron.
- **WinSW:** XML-Config ist git-fuehrbar (`scripts/winsw/curiosity.xml`), Self-Update, klare Service-Semantik.
- **ZIP:** Native Windows, in PowerShell trivial mit `Expand-Archive`/`Compress-Archive`.
- **Auto-Migration:** kleiner Schritt, big win — Andreas muss nicht in zwei Schritten denken.
- **Atomar pro File**: vollatomare Bundle-Replacement-Operationen sind auf Windows schwierig; pro File `Copy-Item` mit Tempnamen + Move ist gut genug, weil Service vorher gestoppt ist.

## Konsequenzen

### Positiv

- Kein Inbound-Port; Public-Web nur ueber CF-Tunnel.
- Admin-Zugang isoliert ueber Tailscale.
- Service ist Auto-Start nach Reboot, restart-on-failure.
- Bundle ist klein, signierbar (Hash-Manifest), reproduzierbar.
- Rollback ist `Stop-Service` + Backup-ZIP entpacken + `Start-Service`.

### Negativ

- Cloudflare ist ein zusaetzlicher Vendor — ohne CF kein Public-Web. Tradeoff: dafuer kein Inbound-Port.
- WinSW-Update muss manuell gemacht werden.
- Bundle-Build ist eine Pflicht-Stufe, kann nicht uebersprungen werden.

### Risiken und Mitigationen

| Risiko | Mitigation |
|---|---|
| Cloudflare-Account weg | Tunnel-Token sind in 1Password, `cloudflared` config in Git |
| WinSW startet uvicorn nicht | Service-Logs in `c:\curiosity\logs\service.log`, restart-on-failure mit Limit |
| Bundle enthaelt versehentlich private Source | Bundle-Builder filtert per Whitelist + Secret-Scan vor Push, Test in pytest |
| Schema-Migration scheitert auf VPS | Auto-Rollback aus Pre-Deploy-Backup |
| `pip install` zerschiesst venv | Venv ist auf VPS dediziert, Backup deckt es ab |
| Tailscale-Outage | RDP-Wartung blockiert temporaer; Public-Web bleibt up, weil unabhaengig |
| `read_models/` ist veraltet im Bundle | Deploy ruft `readmodels rebuild` nach Schema-Migration |

## Bewusst nicht enthalten

- Multi-Region / Failover.
- Login / Auth (Phase D4).
- Schreibendpunkte auf VPS (M5+).
- Container/Docker — Windows-VPS mit nativer Python ist robuster fuer dieses Setup.

## Verweise

- [ADR-0004](ADR-0004-read-only-vps-first.md) — Read-only-Strategie
- [ADR-0006](ADR-0006-source-policy-and-copyright-boundaries.md) — Source-Policy und Copyright
- [ADR-0015](ADR-0015-web-stack-fastapi-jinja2.md) — Web-Stack
- [ADR-0018](ADR-0018-backup-restore-strategy.md) — Backup/Restore (Schwester-ADR)
- [ROADMAP.md](../ROADMAP.md) — M6
