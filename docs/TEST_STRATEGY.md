# Test Strategy

**Status:** v0.1
**Stand:** 2026-05-08

---

## Testprinzipien

1. **Nicht jede Datei braucht denselben Testtyp.**
2. **Jeder kritische Pfad braucht nachvollziehbare Verifikation.**
3. **LLM-Ausgaben werden über Struktur, Quellenbindung und Fixtures geprüft, nicht über blindes Vertrauen.**
4. **Tests müssen Fresh State und Evolved State kennen.**
5. **Rote operative Pfade sind rot, auch wenn Unit Tests grün sind.**
6. **Prompt-Änderungen sind testpflichtig.**
7. **UI-Smoke ist Pflicht, sobald Web-UI im MVP ist.**

## Testschichten

| Schicht | Zweck | Beispiele |
|---|---|---|
| **Unit** | Kleine Logik | Slugs, IDs, Frontmatter, Pfade, Hashing, YAML-Parsing |
| **Contract** | Stabile Schnittstellen | CLI-Commands, Registry-Models, Proposal-Format, Agent-Output-Schema |
| **Data/Wiki Quality** | Wissensqualität | Quellenbindung, Claims, Broken Links, Freshness, Duplicates |
| **Integration** | End-to-End-Pfade | Capture → Extract → Proposal → Review → Publish |
| **LLM Eval** | Synthesequalität | Golden Sources, Claim Fidelity, No-Hallucination Fixtures |
| **UI Smoke** | Browsebarkeit | Home, Seite, Suche, Mobile Layout, Source Drawer |
| **Ops** | Betrieb | Backup, Restore, Rebuild, Health, Deployment Smoke |
| **Docs** | Dokumentations-Integrität | Pfade, Befehle, kanonische Dokumente, ADR-Index |
| **Security** | Schutz | Secret Scan, Raw-Policy, Prompt-Injection-Fixtures |

## Welche Tests pro Phase

| Phase | Unit | Contract | Quality | Integration | Eval | UI | Ops | Docs | Security |
|---|---|---|---|---|---|---|---|---|---|
| **T0.1** | x | – | – | – | – | – | – | x | x |
| **M1** | x | x | – | x | – | – | – | x | x |
| **M2** | x | x | – | x | x (Mock) | – | – | x | x |
| **M3** | x | x | x | x | x | – | – | x | x |
| **M4** | x | x | x | x | x | – | – | x | x |
| **M5** | x | x | x | x | x | x | – | x | x |
| **M6** | x | x | x | x | x | x | x | x | x |

## Markierungen / pytest markers

```python
@pytest.mark.slow
@pytest.mark.integration
@pytest.mark.llm        # echter LLM-Call, default skipped
```

Standard-Run skippt `slow` und `llm`:

```powershell
python -m pytest -q -m "not slow and not llm"
```

Vollständiger Run:

```powershell
python -m pytest -q
python -m pytest -q -m llm    # nur mit LLM-API-Key
```

## Fixtures

```text
tests/fixtures/
  sources/
    unesco_alhambra_short.html
    unesco_alhambra_short.expected.yaml
    pacojet_recipe_short.md
    pacojet_recipe_short.expected.yaml
    product_review_volatile.md
    prompt_injection_source.md       # Injection-Fixture, erwartet Quarantäne
  registry/
    fresh_state.sql
    evolved_state_v0.sql
  pages/
    valid_topic.md
    valid_recipe.md
    invalid_missing_frontmatter.md
    invalid_broken_wikilink.md
```

## Beispiel-Tests pro Schicht

### Unit

```python
def test_id_generator_format():
    sid = generate_source_id()
    assert sid.startswith("src_")
    assert len(sid) >= 24

def test_slugify_german_umlaut():
    assert slugify("Über die Größe") == "ueber-die-groesse"
```

### Contract

```python
def test_cli_help_lists_top_level_commands(cli):
    result = cli.invoke(["--help"])
    assert result.exit_code == 0
    assert "capture" in result.output
    assert "sources" in result.output
```

### Wiki Quality

```python
def test_lint_finds_missing_sources_for_hard_facts(wiki_with_unsourced_claim):
    findings = lint_wiki()
    assert any(f.finding_type == "claim_missing_source" for f in findings)
```

### Integration

```python
@pytest.mark.integration
def test_capture_to_proposal_pipeline(tmp_vault, mock_llm):
    capture_url("https://example.org/test")
    extract_all_pending()
    ingest_all_pending()
    proposals = list_proposals()
    assert len(proposals) == 1
```

### LLM Eval

```python
@pytest.mark.eval
def test_unesco_fixture_creates_place_page(mock_llm_with_fixture):
    proposal = ingest_fixture("unesco_alhambra_short")
    assert any(p.type == "place" for p in proposal.new_pages)
    assert all(p.sources for p in proposal.new_pages)
```

### Security

```python
def test_secret_scan_finds_obvious_keys():
    findings = scan_for_secrets("ANTHROPIC_API_KEY=sk-...")
    assert findings
```

## Golden Questions

Stabile Testfragen, die gegen das Wiki laufen.

```yaml
- id: gq_unesco_001
  question: "Welche UNESCO-Stätten in Frankreich sind in meinem Wiki als Architektur-relevant markiert?"
  required_pages:
    - wiki/topics/unesco-welterbe.md
  expected_behavior:
    - "nennt nur Seiten mit Quellen"
    - "markiert fehlende Aktualität"
    - "erfindet keine nicht vorhandenen Stätten"

- id: gq_pacojet_001
  question: "Welche Faktoren beeinflussen die Textur meiner Pacojet-Sorbets?"
  required_pages:
    - wiki/methods/pacojet-sorbets.md
  expected_behavior:
    - "trennt Quellenwissen von eigenen Experimenten"
    - "nennt Zucker, Alkohol, Fett, Säure nur wenn belegt oder als Methodik markiert"
```

Liegt in `eval/golden-questions.yaml`.

## Coverage-Ziele

| Phase | Coverage |
|---|---|
| T0.1 | 80% (kleine Codebase) |
| M1 | 70% |
| M2 | 65% |
| M3 | 70% |
| M4 | 70% |
| M5 | 60% (UI weniger streng) |
| M6 | 65% |

Coverage-Tool: `pytest-cov`. Ziel-Reports werden in `docs/_ops/quality_gates/` abgelegt.

## CI

Aktuell: lokal (PowerShell-Skripte). Ab M3 oder M4: GitHub Actions mit:

- `pytest`
- `ruff check`
- `ruff format --check`
- Secret Scan
- Optional: Windows Runner für Plattform-Tests

## Verweise

- [VALIDATION_PROTOCOL.md](VALIDATION_PROTOCOL.md) — 10-stufige Validierung
- [EVAL_STRATEGY.md](EVAL_STRATEGY.md) — LLM-Eval im Detail
- [ENGINEERING_MANIFEST.md](ENGINEERING_MANIFEST.md) — Coding-Standards
