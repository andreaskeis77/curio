# ADR-0003: Agent Proposals statt Direktwrites

- **Status:** Accepted
- **Datum:** 2026-05-08
- **Tranche:** T0.1

## Kontext

Das Curiosity Wiki nutzt LLMs zur Synthese-Erzeugung. LLMs können:

- Fakten erfinden (Halluzinationen).
- Inkonsistente Schema-Outputs liefern.
- Prompt-Injection-Angriffe ausführen, wenn Quellen-Inhalt sie dazu auffordert.
- Subtile Formulierungsfehler einbauen, die plausibel klingen.

Wenn LLM-Agenten **direkt** in `wiki/` schreiben, entstehen über Zeit unkontrollierte Qualitätsverluste.

Optionen:

- **A) Direkt-Mutation** — Agent schreibt Wiki-Seite, Mensch liest später.
- **B) Proposal-Pattern** — Agent schreibt nach `proposals/`, Mensch reviewt, dann erst nach `wiki/`.

## Entscheidung

**Option B: Proposal-Pattern. Agenten erzeugen niemals direkt produktive Wiki-Seiten.**

- LLM-Agenten schreiben in `proposals/<run_id>/`.
- Ein Proposal enthält:
  - `proposal.yaml` (Metadaten, IDs)
  - `summary.md` (Mensch-lesbare Übersicht)
  - `patch.diff` (Diff gegen aktuelle Wiki-Seiten, falls Update)
  - `new_pages/` (vorgeschlagene neue Seiten)
  - `updated_pages/` (vorgeschlagene Updates als Diff)
  - `risk_notes.md` (Hinweise auf Halluzination, Injection, Unsicherheit)
- Erst nach **Human Review** (`approve`) wird das Proposal nach `wiki/` geschrieben.

## Begründung

- **Qualitätsschutz:** Halluzinationen werden vor Aufnahme erkannt.
- **Auditierbarkeit:** Jede Änderung hat einen Vorschlag mit Provenienz.
- **Sicherheit:** Prompt-Injection-Folgen werden im Review erkannt.
- **Reversibilität:** Vor Approval kein Schaden.
- **Capsule-Lesson:** Review-first Agentenmodell.

## Konsequenzen

### Positiv

- Kontrollierte Qualität.
- Mensch hat finale Autorität.
- Jede Wiki-Änderung ist nachvollziehbar.
- Kein Auto-Publish-Drift.

### Negativ

- **Mehr manueller Aufwand** für Reviews.
- Bottleneck am Mensch — wenn keine Zeit für Review, stauen sich Proposals.

### Risiken und Mitigationen

| Risiko | Mitigation |
|---|---|
| Proposal-Stau | Lint-Reports priorisieren; einfache Approvals batchbar |
| Mensch übersieht Halluzination | Risk Notes vom Agent zwingend; Lint-Pre-Review-Check |
| Review-UI fehlt im MVP | CLI-Review (`proposal show`/`approve`) reicht für MVP |

## Geplante Review-Stufen

| Stufe | Verfügbar ab |
|---|---|
| CLI Review (`proposal list`, `show`, `approve`) | M3 |
| Web Review Queue (read-only Diffs) | M5 |
| Web Review Queue (interaktive Approve/Edit) | nach MVP, lokal/admin-only |
| Auto-Approve für Low-Risk-Updates | bewusst nicht geplant |

## Verweise

- [ENGINEERING_MANIFEST.md](../ENGINEERING_MANIFEST.md) §Grundprinzipien
- [ARCHITECTURE_REQUIREMENTS_DOSSIER.md](../ARCHITECTURE_REQUIREMENTS_DOSSIER.md) §4
- [concepts/feinkonzept.md](../concepts/feinkonzept.md) §3.4
