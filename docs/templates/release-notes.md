# Release Notes — v<VERSION>

**Datum:** YYYY-MM-DD
**Tag:** v<VERSION>
**Tranche:** <Phase>
**Vorgaenger:** v<VORHERIGE_VERSION>

---

## Highlights

<2–4 Bullets, was in diesem Release wichtig ist>

- …
- …

## Aenderungen

### Hinzugefuegt

- …

### Geaendert

- …

### Entfernt / Deprecated

- …

### Behoben

- …

## Schema-/Daten-Migration

- Schema-Version: <vorher → nachher>
- Migrations-Skripte: `<datei>.sql`
- Read-Models neu zu bauen: ja|nein
- FTS-Index neu zu bauen: ja|nein

## Deploy-Hinweise

- Bundle-Tag: `curiosity-bundle-<sha>-<timestamp>.zip`
- Pre-Deploy-Backup-Pfad: `c:\curiosity\backups\pre-deploy\`
- Erwartete Down-Time: < 30 Sekunden (Service-Restart)
- Rollback-Schritt: `scripts/restore-windows-vps.ps1 -Backup <pfad>`

## Quality Gates

- pytest: <N> passed
- ruff check / format: green
- secret-scan: green
- Smoke (`/healthz/deep`): ok

## Breaking Changes

<keine | Details + Workaround>

## Verweise

- ADR(s) dieser Tranche: ADR-XXXX, ADR-YYYY
- Handoff: `docs/_handoff/<datei>.md`
- ROADMAP §<Phase>
