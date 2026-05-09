# ADR-0010: LLM-Client-Wrapper — Implementierung

- **Status:** Accepted
- **Datum:** 2026-05-08
- **Tranche:** M2 — Extraction & Proposal Ingest
- **Setzt voraus:** [ADR-0007](ADR-0007-llm-client-wrapper-and-prompt-registry.md)

## Kontext

ADR-0007 hat Architektur und Pflichten des LLM-Wrappers festgelegt. Diese ADR konkretisiert die Implementierung für M2.

Anforderungen:

- Provider-agnostische Schnittstelle (`mock`, `anthropic`, `openai`).
- Prompt aus Datei laden, Variablen substituieren, Hash speichern.
- Pydantic-Schema-Validierung des Outputs.
- Run Evidence in `ingest_runs` (prompt_id, prompt_hash, model, parameters, token_usage).
- Mock-Modus deterministisch pro `(source_id, prompt_id)`.
- Timeouts, Retries (exponential backoff), Cost-Logging.

## Entscheidung

### Schnittstelle

```python
class LLMClient:
    def complete(
        self,
        prompt_id: str,
        inputs: dict[str, str],
        output_schema: type[BaseModel],
        *,
        timeout: int | None = None,
        max_retries: int | None = None,
    ) -> tuple[BaseModel, RunEvidence]: ...
```

### Provider-Adapter

Drei Adapter unter `curiosity_wiki/agents/providers/`:

- `mock.py` — deterministischer Stub. Lädt Fixture aus `tests/fixtures/llm_outputs/<prompt_id>/<source_id>.json`, falls vorhanden; sonst minimaler valider Default.
- `anthropic.py` — wickelt `anthropic.Anthropic().messages.create(...)`. Default-Modell `claude-sonnet-4-6`.
- `openai.py` — wickelt `openai.OpenAI().chat.completions.create(...)`. Default-Modell `gpt-4o-mini`.

Alle Adapter implementieren denselben `Provider`-Protocol.

### Prompt-Registry

```text
prompts/
  system/
    source_trust.md
    output_discipline.md
  agents/
    ingest_v0_1.md
```

Prompt-Datei mit YAML-Frontmatter:

```markdown
---
prompt_id: ingest_v0_1
purpose: "Klassifiziere Quelle und schlage Wiki-Seiten vor"
schema_version: 1
inputs:
  - source_metadata
  - extracted_content
output_schema: IngestProposalV1
created: 2026-05-08
---

# Ingest Prompt v0.1

Du bist ein vorsichtiger Wissens-Synthetisierer ...
```

Der Loader berechnet einen SHA-256 über den **Body** der Datei (ohne Frontmatter) und speichert ihn als `prompt_hash`.

### Output-Schema

Pydantic v2. Beispiel für M2:

```python
class IngestProposalV1(BaseModel):
    new_pages: list[ProposedPage]
    hard_facts: list[Claim]
    open_questions: list[str]
    risk_notes: list[RiskNote]
    freshness_recommendation: FreshnessRec
    confidence: ConfidenceLevel
```

### Run Evidence

Alle LLM-Calls schreiben in die Tabelle `ingest_runs`:

```text
id, source_id, prompt_id, prompt_hash, provider, model,
temperature, max_tokens, started_at, finished_at, status,
token_usage_json, error_message
```

`status` ∈ `running | completed | failed | quarantined`.

### Mock-Modus

- Default-Provider in `.env.example` und `config.py`: `mock`.
- Liest Fixtures aus `tests/fixtures/llm_outputs/<prompt_id>/<source_id>.yaml`.
- Wenn keine Fixture: liefert deterministischen Minimal-Output (Title aus extracted Content, type=topic, low confidence, eine open_question).
- Schreibt trotzdem in `ingest_runs` — als `model=mock-1`, `token_usage_json={}`.

### Retries und Timeouts

- Standard-Timeout 60 s (überschreibbar via `CURIOSITY_LLM_TIMEOUT_SECONDS`).
- Bis zu 2 Retries bei `429`, `5xx`, Netzwerkfehlern. Exponentieller Backoff (1 s, 4 s).
- Bei Schema-Validation-Fehler: ein Retry mit Hinweis im Prompt-Suffix; danach Fehler.
- Bei Schema-Fehler **nach** Retry: `status=failed`, kein Proposal geschrieben.

## Begründung

- **Einheitliche Schnittstelle** macht Provider-Wechsel zur Konfigurationssache.
- **Pydantic** liefert Schema-Validation gratis, mit klaren Fehlermeldungen.
- **Mock-Default** lässt Tests ohne API-Keys grün laufen.
- **Run Evidence** ist Pflicht für Replay (NEW NFL Lesson).
- **Prompt-Hash** erkennt unbeabsichtigte Prompt-Änderungen sofort.

## Konsequenzen

### Positiv

- Tests sind kostenfrei.
- Provider-Migration ist eine Stelle.
- Schema-Drift wird erkannt, nicht ignoriert.
- Mock-Outputs sind reviewbar (in Git als Fixtures).

### Negativ

- Pydantic-Dependency.
- Mock-Outputs müssen gepflegt werden.
- Retry-Logik ist eigenes Code-Surface.

## Verweise

- [ADR-0007](ADR-0007-llm-client-wrapper-and-prompt-registry.md) — Architektur
- [PROMPT_REGISTRY.md](../PROMPT_REGISTRY.md)
- [TEST_STRATEGY.md](../TEST_STRATEGY.md) — LLM Eval
