# proposals/

LLM-erzeugte Vorschläge, die noch nicht reviewt sind.

## Pfad-Schema

```text
proposals/<YYYY>/<MM>/<DD>/<run_id>/
  proposal.yaml         # Metadaten, IDs, Targets
  summary.md            # Mensch-lesbare Übersicht
  patch.diff            # Diff gegen aktuelle Wiki-Seiten (bei Updates)
  new_pages/            # vorgeschlagene neue Seiten
  updated_pages/        # Diffs zu existierenden Seiten
  risk_notes.md         # Halluzination, Injection, Unsicherheit
  run_evidence.yaml     # prompt_id, model, parameters, tokens, hash
```

## Workflow

1. LLM-Agent erzeugt Proposal nach Capture/Extract.
2. Pre-Review-Lint prüft Schema, Quellenbindung, plausible Wikilinks.
3. Mensch reviewt mit `curiosity proposal show <id>` und entscheidet:
   - `approve` → Inhalte werden atomar nach `wiki/` geschrieben.
   - `reject` → Proposal bleibt im Archiv, kein Wiki-Schreib.
   - `request-changes` → neue Iteration.
   - `quarantine` → Eintrag in Quarantäne-Registry.

## Regeln

- **Proposals sind Archiv** — sie werden nicht gelöscht (für Replay und Audit).
- Nach Approval bleibt das Proposal als Beleg erhalten.
- Inhalt ist gitignored, außer Beispiel-Fixtures.

## Verweise

- [docs/adr/ADR-0003-agent-proposals-not-direct-writes.md](../docs/adr/ADR-0003-agent-proposals-not-direct-writes.md)
- [docs/ENGINEERING_MANIFEST.md](../docs/ENGINEERING_MANIFEST.md)
