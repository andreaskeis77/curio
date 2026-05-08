# ADR-0006: Source Policy and Copyright Boundaries

- **Status:** Accepted
- **Datum:** 2026-05-08
- **Tranche:** T0.1

## Kontext

Das Curiosity Wiki sammelt Quellen aus dem Web, aus PDFs, aus eigenen Notizen, und plant später auch Produkttests und Mode-Recherchen. Diese Inhalte unterliegen unterschiedlichen rechtlichen und ethischen Beschränkungen:

- **Wikipedia-Artikel** sind unter freier Lizenz (CC-BY-SA).
- **Bezahlte Testberichte** sind urheberrechtlich geschützt.
- **Paywall-Artikel** sind oft nur für Abonnenten.
- **Eigene Notizen** sind privat.
- **Werbe-Material** kann irreführend sein.

Wenn das System diese Quellen ohne Klassifizierung speichert und LLM-mäßig verarbeitet, riskieren wir:

- Urheberrechtsverletzungen.
- Datenschutz-Probleme.
- Falsches Vertrauen in Marketing-Material.
- Versehentliches Veröffentlichen privater Inhalte.

## Entscheidung

**Source Policy ist Pflicht ab T0.1, nicht erst nach problematischem Ingest.**

Jede Quelle bekommt im Manifest:

- `access`: `public | private | paywalled | own_note`
- `copyright_risk`: `low | medium | high`
- `reliability`: `official | expert | journalistic | commercial | personal | unknown`
- `llm_allowed`: `true | false`

Speicher- und Verarbeitungsregeln nach Klasse — siehe [SOURCE_POLICY.md](../SOURCE_POLICY.md).

**Hard Rules:**

1. `access: paywalled` oder `copyright_risk: high` → **kein** Volltext-Speichern.
2. `access: private` oder `own_note` → bleibt lokal, geht **nie** in Public-Bundle.
3. `llm_allowed: false` → kein Volltext an LLM, nur eigene Notizen + Metadaten.

## Begründung

- **Rechtssicherheit:** Klare Grenzen pro Quelle.
- **Privatsphäre:** Private Notizen sind klar markiert.
- **Synthese-Qualität:** Reliability-Marker helfen LLM und Mensch, Marketing von Fakten zu unterscheiden.
- **Capsule-Lesson:** Source Policy früh.
- **NEW NFL Lesson:** Quarantäne für policy-kritische Quellen.

## Konsequenzen

### Positiv

- Klarer Umgang mit kritischen Quellen.
- Schutz vor versehentlicher Veröffentlichung.
- Bewusste Entscheidung pro Quelle.

### Negativ

- **Zusätzlicher Capture-Aufwand:** Klassifizierung muss bei jeder Quelle erfolgen.
- Manche Klassifizierungen sind initial unklar — Default `unknown` und Review.

### Risiken und Mitigationen

| Risiko | Mitigation |
|---|---|
| Capture wird zu mühsam | Defaults: `access: public`, `copyright_risk: low` für offensichtliche Quellen; Override per Flag |
| Falsche Klassifizierung | Lint-Findings bei verdächtigen Mustern |
| Policy-Änderungen über Zeit | Manifest-Versionierung, Re-Classification-Job |

## Pflicht-Workflow bei Capture

```python
def capture_url(url: str, why: str, **classifiers) -> Source:
    # Default-Heuristik anhand Domain (z.B. wikipedia.org → public/low)
    defaults = guess_classifiers(url)
    # User kann via Flags überschreiben
    classifiers = {**defaults, **classifiers}
    # Bei high-risk muss user bewusst confirmen
    if classifiers["copyright_risk"] == "high":
        require_explicit_flag("--accept-high-copyright-risk")
    # ...
```

## Pre-Deploy-Filter (ab M6)

Bei VPS-Bundle-Erstellung:

```text
filter_out_if:
  access in (private, paywalled)
  copyright_risk in (high)
  llm_allowed == false  # für LLM-erzeugte Inhalte
```

## Verweise

- [SOURCE_POLICY.md](../SOURCE_POLICY.md)
- [SECURITY.md](../SECURITY.md)
- [ARCHITECTURE_REQUIREMENTS_DOSSIER.md](../ARCHITECTURE_REQUIREMENTS_DOSSIER.md) §10
