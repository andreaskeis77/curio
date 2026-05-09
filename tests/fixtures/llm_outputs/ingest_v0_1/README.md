# LLM-Output-Fixtures für `ingest_v0_1`

Mock-Provider lädt YAML-Fixtures aus diesem Verzeichnis pro `(prompt_id, source_id)`.

Da Source-IDs zur Laufzeit generiert werden (`src_<timestamp>_<rand>`),
lassen Tests den Mock-Provider standardmäßig auf den Default-Output
fallen (`agents/providers/mock.py` → `DEFAULT_INGEST_OUTPUT`).

Wer einen spezifischen Mock-Output für einen Test setzen will, kopiert
beim Setup die Fixture nach `tests/fixtures/llm_outputs/ingest_v0_1/<source_id>.yaml`
(z.B. via `tmp_path.copy_to`).

## Beispiel-Fixture

```yaml
new_pages:
  - title: "Alhambra"
    slug: "alhambra"
    type: "place"
    sources: ["src_..."]
    sections:
      - heading: "Kurzfassung"
        markdown: "Die Alhambra ist ..."
    open_questions:
      - "Welche anderen maurischen Bauwerke sind im Wiki relevant?"
    confidence: "high"
hard_facts:
  - claim_text: "Aufnahme in die UNESCO-Welterbeliste 1984."
    claim_type: "year"
    source_id: "src_..."
    confidence: "high"
risk_notes: []
freshness_recommendations:
  - page_title: "Alhambra"
    freshness: "stable"
overall_confidence: "high"
summary: "UNESCO-Welterbe Alhambra in Granada — stabiles Faktenwissen."
```
