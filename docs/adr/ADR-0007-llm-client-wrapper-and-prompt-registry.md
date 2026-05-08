# ADR-0007: LLM Client Wrapper und Prompt Registry

- **Status:** Accepted
- **Datum:** 2026-05-08
- **Tranche:** T0.1 (Architektur), Implementierung in M2

## Kontext

Das Curiosity Wiki nutzt LLMs zur Klassifizierung, Synthese, Lint-Bewertung, Query-Beantwortung und später für Update Scouts. Risiken bei direkter Nutzung von Anbieter-SDKs:

- **Lock-in** auf einen Provider.
- **Fehlende Standardisierung** von Timeouts, Retries, Cost-Logging.
- **Keine Mock-Möglichkeit** für Tests ohne API-Calls.
- **Kein zentrales Prompt-Versioning.**
- **Kein Schema-Validation** von Outputs.

Optionen:

- **A) Direkter Provider-Aufruf** — `anthropic.client.create()` überall.
- **B) Eigener Wrapper** — `LLMClient.complete(prompt_id, inputs) -> StructuredOutput`.

## Entscheidung

**Option B: Eigener LLM-Client-Wrapper plus Prompt Registry.**

### LLM Client

```python
class LLMClient:
    def complete(
        self,
        prompt_id: str,
        inputs: dict,
        output_schema: type[BaseModel],
        timeout: int = 60,
        max_retries: int = 2,
    ) -> tuple[BaseModel, RunEvidence]:
        ...
```

Der Wrapper:

- Lädt Prompt aus `prompts/agents/<prompt_id>.md`.
- Substituiert `inputs`-Variablen.
- Ruft Provider-SDK auf (Anthropic / OpenAI / Mock).
- Validiert Output gegen Schema.
- Loggt `prompt_id`, `prompt_hash`, `model`, `parameters`, `tokens` in `ingest_runs`.
- Wirft Exception bei Schema-Fehler oder Timeout.
- Mock-Modus liefert Fixture-Output für Tests.

### Prompt Registry

- Alle Prompts in `prompts/agents/` als Markdown mit Frontmatter.
- Eintrag in `docs/PROMPT_REGISTRY.md`.
- Version im Prompt-ID (`ingest_v0_3`).
- Hash bei Laufzeit berechnet, in Run Evidence gespeichert.
- Alte Versionen werden behalten (für Replay).

## Begründung

- **Provider-Unabhängigkeit:** Wechsel zwischen Anthropic/OpenAI ohne Code-Änderungen außerhalb des Wrappers.
- **Test-Bar:** Mock-Modus ermöglicht deterministische Tests.
- **Run Evidence:** Replay erfordert klare Provenienz.
- **Schema-Validation:** LLM-Schema-Drift wird sofort erkannt.
- **Cost-Logging:** Token-Verbrauch ist nachvollziehbar.
- **Capsule + NEW NFL Lesson:** LLM-Output ist untrusted, bis geprüft.

## Konsequenzen

### Positiv

- Saubere Architektur-Schicht.
- Tests funktionieren ohne API-Key.
- Alle Provider haben dieselbe Schnittstelle.
- Prompt-Versionierung erzwungen.

### Negativ

- **Zusätzliche Abstraktionsschicht** zu warten.
- Provider-spezifische Features (Tool Use, Streaming) erfordern Erweiterung des Wrappers.

### Risiken und Mitigationen

| Risiko | Mitigation |
|---|---|
| Wrapper hinkt Provider-Updates hinterher | Modulare Provider-Adapter, klare Versionierung |
| Mock-Mode divergiert von echten Outputs | Mock-Fixtures aus echten LLM-Outputs ableiten, regelmäßig refreshen |
| Schema-Verletzung blockt Pipeline | Klare Fehlermeldung, Quarantäne-Eintrag, kein Wiki-Schreib |

## Default-Konfiguration (T0.1)

```python
DEFAULT_PROVIDER = "mock"
DEFAULT_TIMEOUT = 60
DEFAULT_MAX_RETRIES = 2
DEFAULT_TEMPERATURE = 0
```

In M2 wird `anthropic` mit `claude-sonnet-4-6` als prod-Default ergänzt.

## Verweise

- [PROMPT_REGISTRY.md](../PROMPT_REGISTRY.md)
- [ENGINEERING_MANIFEST.md](../ENGINEERING_MANIFEST.md) §LLM-Regeln
- [TEST_STRATEGY.md](../TEST_STRATEGY.md)
- [ARCHITECTURE_REQUIREMENTS_DOSSIER.md](../ARCHITECTURE_REQUIREMENTS_DOSSIER.md) §4 (Layer 5)
