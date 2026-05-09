# ADR-0018: Backup- und Restore-Strategie

- **Status:** Accepted
- **Datum:** 2026-05-09
- **Tranche:** M6 — VPS Read-only Preview
- **Verwandt:** [ADR-0017](ADR-0017-vps-deployment-model.md) (VPS-Deployment)

## Kontext

ADR-0017 setzt voraus, dass jeder Deploy mit einem Backup beginnt und im Fehlerfall zurueckgerollt werden kann. ADR-0018 fixiert **wie** Backups erzeugt, geprueft und wieder eingespielt werden.

Anforderungen:

- **Vor jedem Deploy** automatisches Backup, ohne Andreas-Interaktion.
- **Taeglich** (auch ohne Deploy) ein Backup, um auch unbeabsichtigte Datenverluste abzudecken.
- **Restore-Drill** mindestens einmal vor Live-Schaltung, danach quartalsweise.
- **Hash-Manifest** pro Backup, damit Integritaet nachweisbar.
- **Lokal** (auf VPS) plus optional Off-Site (Andreas-Laptop ueber Tailscale).
- **Klein**: Wiki ist Markdown + JSON, ein Backup darf maximal 10–50 MB werden.

Offene Fragen:

1. **Was kommt ins Backup?** Nur Daten (DB + Wiki) oder auch Code/Config?
2. **Format**: ZIP, tar, xz?
3. **Aufbewahrung**: wie viele Backups, wie lange?
4. **Off-Site**: passiv (rsync/Tailscale-Pull) oder aktiv (rclone-Push)?
5. **Restore-Verifikation**: nur Hash, oder auch Smoke-Test?

## Entscheidung

**Voller VPS-Snapshot in ZIP, taeglich + pre-deploy, lokale Aufbewahrung 14 Tage + monatlicher Snapshot 12 Monate, Off-Site passiv via Tailscale-Pull, Restore-Drill mit Smoke-Test verifiziert.**

### Backup-Inhalt

Pro Backup wird ein ZIP erzeugt mit:

```text
curiosity-backup-<timestamp>.zip
├── manifest.json           # version, created_at, file_hashes (SHA-256), bytes_total
├── data/registry/          # SQLite (live oder konsistente Kopie via VACUUM INTO)
├── wiki/                   # Markdown-Pages
├── read_models/            # gebaute Read-Models
├── prompts/                # Prompt-Registry
├── eval/                   # Goldens
├── pyproject.toml
└── runtime/
    └── service.xml         # WinSW-Config (damit Restore identisch laeuft)
```

**Nicht im Backup:**

- `raw/` — bleibt ausschliesslich auf Andreas-Laptop. **VPS hat keine Raw-Snapshots**, daher gibt es nichts zu sichern.
- `proposals/` — auf VPS irrelevant (Read-only).
- `extracted/` — wie oben.
- `.env` — nicht in den Repo, nicht ins Backup.
- `docs/_ops/` — operative Logs, koennen sich VPS-seitig ansammeln; werden separat rotiert.
- `.venv/` — Re-Install ist deterministisch ueber `pyproject.toml`.

### Manifest-Format

```json
{
  "schema_version": 1,
  "created_at": "2026-05-09T03:00:00Z",
  "host": "VPS-CURIOSITY",
  "git_sha": "<sha-falls-bekannt>",
  "package_version": "0.7.0",
  "files": [
    {"path": "data/registry/curiosity.sqlite", "sha256": "…", "bytes": 12345}
  ],
  "bytes_total": 1234567
}
```

Manifest wird **vor** dem ZIP-Inhalt erstellt; ZIP enthaelt es unter `manifest.json`. Restore validiert **alle** SHA-256 vor dem Einspielen.

### Erzeugungs-Pfad

- **Pre-Deploy** (siehe `scripts/backup-windows-vps.ps1`): wird vom Deploy-Skript synchron aufgerufen.
- **Daily**: Windows-Scheduled-Task `c:\curiosity\scripts\backup-windows-vps.ps1`, taeglich 03:00.

Beide nutzen das gleiche Skript. Unterschied: Pre-Deploy markiert den Filename mit `pre-deploy-<deploy_id>`, Daily mit `daily`.

### Aufbewahrung

- **VPS-lokal**: rolling, 14 Tage taeglich + letzte Pre-Deploys + monatlicher Snapshot vom 1. fuer 12 Monate. Aufraeumen via Skript am Ende jedes Backup-Laufs.
- **Off-Site (Andreas-Laptop)**: passiv — Andreas zieht alle 1–2 Wochen via `scripts/pull-vps-backups.ps1` ueber Tailscale ein delta. Skript loescht **nichts**.
- **Encryption**: nicht im MVP. Wenn Backups Off-Site auf einen Cloud-Bucket gehen sollen, wird das in einem spaeteren ADR adressiert (mit GPG- oder age-Keys).

### Restore-Verifikation

Restore-Skript laeuft so:

1. Backup-ZIP entpacken nach `c:\curiosity\restore-staging\`.
2. Manifest laden.
3. Pro File: SHA-256 nachrechnen, Mismatch → Abbruch.
4. Service stoppen.
5. Live-Verzeichnis nach `c:\curiosity\rollback-<timestamp>` umbenennen.
6. Staging-Inhalte ins Live-Verzeichnis kopieren.
7. Service starten.
8. **Smoke-Test**: `curl http://127.0.0.1:8765/healthz/deep` muss `status: ok` liefern, sonst Rollback aus Schritt 5.

Restore-Drill-Prozedur ist im RUNBOOK dokumentiert.

### Off-Site-Pull (Andreas-Laptop)

Skript `scripts/pull-vps-backups.ps1` (Andreas-Laptop):

```powershell
# Tailscale muss aktiv sein.
$ErrorActionPreference = "Stop"
$tailscaleHost = "vps-curiosity"
$localDir = "c:\curiosity\offsite-backups"
robocopy "\\$tailscaleHost\backups" $localDir /MIR /R:2 /W:5 /NFL /NDL
```

`/MIR` haben wir bewusst NICHT — wir spiegeln **nicht**, sondern ergaenzen, damit lokale Kopien nicht versehentlich verschwinden.

```powershell
robocopy "\\$tailscaleHost\backups" $localDir /E /XO /R:2 /W:5
```

`/XO` = nur kopieren, wenn neuer; `/E` = inklusive Unterordner.

## Begründung

- **ZIP** ist Windows-nativ, integrieren von WinSW-Config + DB + Files in einem File ist trivial.
- **VACUUM INTO** statt File-Copy fuer SQLite — verhindert WAL-Inkonsistenzen mid-write. Falls VACUUM zu langsam, Fallback auf normalen Copy mit `PRAGMA wal_checkpoint(TRUNCATE)` davor.
- **14 Tage rolling + 12 Monate monatlich** ist ein klassisches GFS-leichteres Schema, passt zu kleinem Wiki.
- **Hash-Manifest** macht Korruption sichtbar; ohne wuerde ein Bit-Fehler stillschweigend das Wiki kaputtmachen.
- **Off-Site passiv per Tailscale-Pull**: kein Cloud-Account noetig im MVP; Andreas-Laptop hat alles.

## Konsequenzen

### Positiv

- Backup-Erzeugung und -Aufbewahrung sind in einem Skript zentralisiert.
- Restore ist ein einzelnes Skript mit klarer Smoke-Verifikation.
- Pre-Deploy-Backup bedeutet jeder Deploy hat einen Auto-Rollback-Punkt.
- Kein Cloud-Vendor noetig.

### Negativ

- Off-Site-Backups sind nur so frisch wie Andreas-Pull-Cadence. Wenn 6 Wochen kein Pull, kann ein VPS-Totalverlust 6 Wochen kosten. Mitigation: Calendar-Reminder + ggf. Cloud-Off-Site spaeter.
- Backup ist nicht verschluesselt im MVP — Andreas-Laptop und VPS sind beide vertrauenswuerdig, aber ein Cloud-Push wuerde GPG/age erfordern.
- Falls VACUUM INTO unter Lock blockiert, faellt das Skript zurueck auf File-Copy mit Checkpoint — kann zu Teil-WAL fuehren, aber Restore wuerde das beim Hash-Check sehen.

### Risiken und Mitigationen

| Risiko | Mitigation |
|---|---|
| Backup-Lauf verschlingt Disk | 14d-Rolling cleanup, Skript bricht bei < 1 GB freiem Platz ab |
| SQLite-WAL aktiv waehrend Backup | `VACUUM INTO` als Default, Fallback File-Copy mit `wal_checkpoint(TRUNCATE)` |
| Manifest stimmt nicht mit Inhalt | Restore prueft alle SHA-256 vor dem Einspielen |
| Andreas vergisst Off-Site-Pull | RUNBOOK-Reminder, Calendar-Eintrag |
| Restore-Drill nie ausgefuehrt | Pflicht-Schritt vor Live-Schaltung, dokumentiert in RUNBOOK |
| Backup enthaelt versehentlich private Source | VPS hat **keine** privaten Sources (siehe ADR-0006), Backup ist daher schon per Konstruktion sauber |

## Backup-Schedule (Zusammenfassung)

| Trigger | Skript | Zielordner | Aufbewahrung |
|---|---|---|---|
| Vor jedem Deploy | `backup-windows-vps.ps1 -Reason pre-deploy` | `c:\curiosity\backups\pre-deploy\` | 30 Tage |
| Taeglich 03:00 | `backup-windows-vps.ps1 -Reason daily` | `c:\curiosity\backups\daily\` | 14 Tage |
| Monatlich 1. 03:30 | `backup-windows-vps.ps1 -Reason monthly` | `c:\curiosity\backups\monthly\` | 12 Monate |
| Off-Site Pull | `pull-vps-backups.ps1` (Laptop) | `c:\curiosity\offsite-backups\` | rein additiv |

## Bewusst nicht enthalten

- Verschluesselung im MVP.
- Cloud-Off-Site-Storage (S3, B2) — bei Bedarf eigenes ADR.
- Continuous Backup mit Point-in-Time-Recovery — fuer ein Wiki-System overkill.
- Multi-Region-Replication.

## Verweise

- [ADR-0006](ADR-0006-source-policy-and-copyright-boundaries.md) — Source-Policy
- [ADR-0017](ADR-0017-vps-deployment-model.md) — VPS-Deployment
- [RUNBOOK.md](../RUNBOOK.md) — Restore-Drill-Prozedur
- [ROADMAP.md](../ROADMAP.md) — M6
