# extracted/

Extrahierter Text aus Raw Sources, normalisiert als Markdown mit Metadaten-Header.

## Pfad

```text
extracted/<source_id>.md
```

## Inhalt pro Datei

```markdown
---
source_id: src_...
extracted_at: 2026-05-08T14:30:12+02:00
extractor: trafilatura | markitdown | pypdf | passthrough
extractor_version: ...
warnings: []
---

# Original Title

<extrahierter Text>
```

## Regeln

- **Regenerierbar** aus Raw Sources. Bei Verlust: Re-Extraction.
- **Inkonsistente Extraktion** → Fehler in Manifest, kein Fortschritt für diese Source.
- Extracted Markdown wird vom LLM-Ingest gelesen.

## Git-Behandlung

`extracted/*` ist gitignored, außer Beispiel-Fixtures explizit committed.
