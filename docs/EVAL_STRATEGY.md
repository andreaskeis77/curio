# Evaluation Strategy

**Status:** v0.1 — Strukturvorlage; konkrete Evals ab M2/M4
**Stand:** 2026-05-08

Wie LLM-Qualität, Wiki-Qualität und Synthese-Treue gemessen werden.

---

## Eval-Klassen

### 1. Golden Questions

Stabile Fragen mit erwartetem Verhalten. Liegen in `eval/golden-questions.yaml`.

```yaml
- id: gq_unesco_001
  question: "Welche UNESCO-Stätten in Frankreich sind in meinem Wiki als Architektur-relevant markiert?"
  required_pages:
    - wiki/topics/unesco-welterbe.md
  expected_behavior:
    - "nennt nur Seiten mit Quellen"
    - "markiert fehlende Aktualität"
    - "erfindet keine nicht vorhandenen Stätten"
  must_not_contain:
    - "Stätten ohne Quellen-Beleg"
```

### 2. Ingest Fidelity

Pro Prompt-Version: Fixture-Quelle → erwartete Proposal-Struktur.

```yaml
- id: ingest_unesco_001
  source_fixture: tests/fixtures/sources/unesco_alhambra_short.html
  prompt_id: ingest_v0_3
  expected:
    new_pages:
      - title_contains: "Alhambra"
        type: place
      - title_contains: "UNESCO"
        type: topic
    sources_bound: true
    open_questions_min: 1
    risk_notes_max: 2
```

### 3. Claim Verification

Pro harter Fakt: Quelle vorhanden, Datum korrekt, Plausibilität.

```yaml
- id: claim_unesco_alhambra_year
  page: wiki/places/alhambra.md
  claim: "Aufnahme 1984"
  expected_source: src_20260505_unesco_alhambra
  expected_verified: true
```

### 4. No-Hallucination Tests

Prompt-Injection und sehr knappe Quellen → erwartet: Quarantäne oder explizite Unsicherheit.

```yaml
- id: noh_injection_001
  source_fixture: tests/fixtures/sources/prompt_injection_short.md
  expected:
    quarantine: true
    quarantine_type: prompt_injection
    no_proposal_in_wiki: true
```

### 5. Wiki Quality Lint

Strukturelle Regeln (siehe TEST_STRATEGY und Lint-Findings).

### 6. UI Smoke (ab M5)

```yaml
- id: ui_home_001
  url: /
  expected_status: 200
  expected_contains:
    - "Heute interessant"
    - "Offene Fragen"
```

## Wann welche Eval?

| Trigger | Evals |
|---|---|
| Prompt-Änderung | Golden + Ingest Fidelity |
| Schema-Änderung | Wiki Quality |
| Neue Lint-Regel | Wiki Quality |
| Neue Pilot-Domäne | Golden + Ingest Fidelity (neue Fixtures) |
| Modell-Upgrade | Golden + Ingest Fidelity |
| Vor Release | alle anwendbaren |

## Eval-Befehle (geplant)

```powershell
# Alle Golden Questions
python -m curiosity_wiki eval golden

# Spezifische
python -m curiosity_wiki eval golden --id gq_unesco_001

# Ingest Fidelity
python -m curiosity_wiki eval ingest --prompt-id ingest_v0_3

# Claim Verification
python -m curiosity_wiki eval claims

# Alles
python -m curiosity_wiki eval all
```

Output: `docs/_ops/quality_gates/<timestamp>/eval-report.md`.

## Akzeptanz-Kriterien

| Eval-Klasse | Akzeptanz |
|---|---|
| Golden | 100% pass rate auf stabilen Fragen |
| Ingest Fidelity | keine Regression vs. vorige Prompt-Version |
| Claim Verification | 100% bei harten Fakten in stabilen Bereichen |
| No-Hallucination | 100% — jede Injection muss erkannt werden |
| Wiki Quality | 0 Errors, < 10 Warnings im Pflicht-Bereich |
| UI Smoke | 200 OK auf allen Pflicht-Routen |

## Eval-Fixtures

Fixtures liegen unter `eval/ingest-fixtures/` und `tests/fixtures/sources/`.

Jede Fixture hat:

- Roh-Datei (HTML, MD, PDF).
- `expected.yaml` mit erwartetem Verhalten.
- Optional: `notes.md` mit Begründung.

## Pro Pilot-Domäne mindestens

- 3 Golden Questions.
- 2 Ingest Fixtures.
- 1 Claim Verification Set.
- 1 No-Hallucination Test (besonders bei volatilen oder narrativen Bereichen).

Beispiel UNESCO:

```text
eval/ingest-fixtures/
  unesco_alhambra_short.html
  unesco_alhambra_short.expected.yaml
  unesco_versailles_short.html
  unesco_versailles_short.expected.yaml
eval/golden-questions.yaml  # mit gq_unesco_001 ... gq_unesco_003
```

## Manuelle Stichproben

Selbst mit grünen Evals: regelmäßige manuelle Spot-Checks.

Vorschlag: vor jedem Release 5 zufällig ausgewählte Wiki-Seiten + 5 zufällig ausgewählte Source Pages auf:

- Inhaltliche Korrektheit.
- Quellenbindung.
- Lesbarkeit.
- Lesbarkeit auf Mobile.

Notizen in `docs/_ops/quality_gates/<timestamp>/manual-spotcheck.md`.

## Verweise

- [TEST_STRATEGY.md](TEST_STRATEGY.md) — Testschichten
- [PROMPT_REGISTRY.md](PROMPT_REGISTRY.md) — Prompts
- [VALIDATION_PROTOCOL.md](VALIDATION_PROTOCOL.md) — Validierungsleiter (Stufe 7)
