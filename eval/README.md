# eval/

Evaluation-Fixtures und Golden Questions.

## Struktur

```text
eval/
  golden-questions.yaml     # Stabile Testfragen
  ingest-fixtures/          # Quellen-Fixtures mit erwartetem Output
    unesco_alhambra_short.html
    unesco_alhambra_short.expected.yaml
  expected-reports/         # Erwartete Lint-Reports für Tests
```

## Konkretisierung ab M2

- Erste Golden Questions für UNESCO und Pacojet.
- Erste Ingest Fixtures für jede Pilot-Domäne.
- Prompt-Injection-Fixture als No-Hallucination-Test.

## Verweise

- [docs/EVAL_STRATEGY.md](../docs/EVAL_STRATEGY.md)
