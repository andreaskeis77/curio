# ADR-0001: Markdown plus SQLite Registry

- **Status:** Accepted
- **Datum:** 2026-05-08
- **Tranche:** T0.1

## Kontext

Das Curiosity Wiki braucht eine Persistenz-Schicht, die zwei sehr unterschiedliche Anforderungen erfüllt:

1. **Wissensinhalte** sind langlebig, müssen menschenlesbar sein, gut diffbar, mit Obsidian kompatibel, in Git versionierbar.
2. **Operative Zustände** (Quellen-Status, Jobs, Claims, Freshness, Proposals, Lint-Findings, Run Evidence) brauchen transaktionale Integrität, Indizierung, schnelle Abfragen.

Optionen:

- **A) Nur Markdown** — alles in Frontmatter und Dateinamen kodieren.
- **B) Nur Datenbank** — Postgres oder SQLite, Markdown als Export.
- **C) Markdown + SQLite (Hybrid)** — Markdown als Wissens-Wahrheit, SQLite als operativer Index.

## Entscheidung

**Option C: Markdown + SQLite Registry.**

- Markdown-Dateien mit YAML-Frontmatter sind die **menschenlesbare Wissens-Wahrheit**.
- SQLite (in `data/registry/curiosity.sqlite`) hält **operative Zustände**: Sources, Runs, Claims, Proposals, Lint-Findings, Jobs.
- UI liest aus beiden Schichten plus Read Models.
- Bei Verlust der Registry ist sie aus Markdown + Source Manifests rekonstruierbar (außer Job-Historie, Reviews, Timing-Daten).

## Begründung

- **Langlebigkeit:** Markdown ist offen, plain text, in 30 Jahren noch lesbar.
- **Tooling:** Obsidian, VS Code, GitHub, Pandoc — alle verstehen Markdown.
- **Diffbar:** Markdown-Diffs in Git sind menschlich lesbar.
- **Operativer Bedarf:** Markdown allein reicht nicht für: schnellen Status-Lookup, Jobs, Replay-Evidence, Indexierung.
- **SQLite ist robust:** Kein Server, dateibasiert, transaktional, gut zu sichern.
- **Rebuildbarkeit:** Wenn nötig, kann Registry verworfen und neu aufgebaut werden.

## Konsequenzen

### Positiv

- Wissensinhalte sind portabel.
- Operative Zustände sind sauber getrennt.
- SQLite-Backup ist eine einzelne Datei.
- Mehrere Tools können Markdown lesen.

### Negativ

- **Doppelte Wahrheit** — Markdown-Frontmatter und Registry können divergieren.
- Synchronisation ist nötig (z.B. nach manuellen Markdown-Edits).
- Komplexität: zwei Persistenz-Layer statt einer.

### Risiken und Mitigationen

| Risiko | Mitigation |
|---|---|
| Frontmatter und Registry divergieren | `curiosity registry sync` Befehl, Validation Gate |
| Manuelle Markdown-Edits umgehen Registry | Pre-Commit-Hook (später), Lint-Findings |
| Registry-Korruption | Backups, Rebuild aus Markdown möglich |

## Verweise

- [ARCHITECTURE_REQUIREMENTS_DOSSIER.md](../ARCHITECTURE_REQUIREMENTS_DOSSIER.md) §5
- [concepts/feinkonzept.md](../concepts/feinkonzept.md) §3.2
