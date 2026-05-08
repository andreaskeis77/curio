# prompts/

LLM-Prompts mit Versionierung. Konkrete Prompts entstehen ab M2.

## Struktur

```text
prompts/
  system/                # Universal-Prefixes (Source Trust, Output Discipline)
  agents/
    ingest.md            # Ingest-Prompt (M2)
    link.md              # Link-Vorschläge
    lint.md              # Lint-Bewertung
    query.md             # Query-Antworten
    browse.md            # Lesepfade
    update_scout.md      # Update-Scouts (M7)
  eval/                  # Eval-Prompts und Test-Setups
```

## Regeln

- Jeder Prompt hat **ID, Version, Schema, Tests, Risiken** im Frontmatter.
- Eintrag in [docs/PROMPT_REGISTRY.md](../docs/PROMPT_REGISTRY.md).
- Alte Versionen bleiben erhalten (für Replay).
- Prompt-Änderungen sind **testpflichtig** (Golden Questions, Ingest Fidelity).

## Verweise

- [docs/PROMPT_REGISTRY.md](../docs/PROMPT_REGISTRY.md)
- [docs/adr/ADR-0007-llm-client-wrapper-and-prompt-registry.md](../docs/adr/ADR-0007-llm-client-wrapper-and-prompt-registry.md)
