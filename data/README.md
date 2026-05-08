# data/

Operative Daten des Systems.

## Struktur

```text
data/
  registry/
    curiosity.sqlite          # Haupt-Registry (gitignored)
  seeds/
    <Seeds für Tests>
  fixtures/
    <Test-Fixtures>
```

## Regeln

- `data/registry/*.sqlite` ist gitignored.
- Backup-Strategie: vor jedem Deployment.
- Rebuild-Möglichkeit: `curiosity registry rebuild-from-markdown` (kommt in M3+).

## Verweise

- [docs/adr/ADR-0001-markdown-plus-sqlite-registry.md](../docs/adr/ADR-0001-markdown-plus-sqlite-registry.md)
- [docs/RUNBOOK.md](../docs/RUNBOOK.md) — Backup/Restore
