# ADR-0002: Immutable Raw Sources

- **Status:** Accepted
- **Datum:** 2026-05-08
- **Tranche:** T0.1

## Kontext

Quellen ändern sich im Web (URL ändert Inhalt, Paywall wird strenger, Artikel wird zurückgezogen). Wenn das Curiosity Wiki Aussagen aus Quellen synthetisiert, muss nachvollziehbar bleiben, **welche Version** einer Quelle die Synthese gestützt hat.

Optionen:

- **A) Quellen werden bei jedem Update überschrieben** — einfacher, weniger Speicher.
- **B) Quellen-Snapshots sind immutable** — neue Version bei erneutem Abruf.

## Entscheidung

**Option B: Immutable Raw Sources.**

- Jeder Capture erzeugt einen **Snapshot** mit Hash und Zeitstempel.
- Snapshots werden **nie überschrieben**.
- Erneuter Abruf erzeugt einen **neuen Snapshot**, falls Inhalt sich geändert hat.
- Snapshots liegen in `raw/` mit dem Pfad-Schema:
  ```
  raw/<source_type>/<YYYY>/<MM>/<DD>/<source_id>/<original_filename>
  ```
- Manifest enthält `sha256` zur Versionsverifikation.

## Begründung

- **Replay:** Eine Wiki-Aussage muss zur Quelle dieser Zeit zurückführbar sein.
- **Audit:** Wenn ein Fakt sich später als falsch herausstellt, muss klar sein, ob die Quelle damals anders war.
- **Diff:** Versionsvergleich zwischen Snapshots ist möglich.
- **Schutz vor stiller Manipulation:** Wenn die Original-URL ihren Inhalt ändert, bleibt unsere Synthese nachprüfbar.
- **NEW NFL Lesson:** Immutable Raw-Landing ist Pflicht für Replay.

## Konsequenzen

### Positiv

- Reproduzierbarkeit der Synthese.
- Audit-Trail ohne externe Dienste.
- Diff zwischen Quellenversionen möglich.
- Schutz vor unbeabsichtigtem Datenverlust.

### Negativ

- **Speicher** wächst über Zeit (PDFs, HTML-Snapshots, Screenshots).
- Mehrere Snapshots derselben URL können den Vault aufblähen.

### Risiken und Mitigationen

| Risiko | Mitigation |
|---|---|
| Speicher-Wachstum | Klare `.gitignore`-Strategie, Manifest+Hash in Git, große Blobs lokal-only |
| Versehentliches Löschen von Snapshots | Backups, Lint-Warnung wenn Source ohne Snapshot |
| Zwischen-Versionen verloren | Erneuter Capture wird empfohlen, wenn relevante Änderung erwartet |

## Quellen-Speicher-Pfad-Schema

```text
raw/
  inbox/
    <freie Capture-Notizen, später sortiert>
  web/
    2026/05/08/
      src_20260508_141204_unesco_alhambra/
        original.html
        metadata.yaml
        content.sha256
  pdf/
    2026/05/08/
      src_.../
        original.pdf
        metadata.yaml
        content.sha256
  screenshots/
  notes/
  data/
```

## Verweise

- [ARCHITECTURE_REQUIREMENTS_DOSSIER.md](../ARCHITECTURE_REQUIREMENTS_DOSSIER.md) §5
- [SOURCE_POLICY.md](../SOURCE_POLICY.md)
- [concepts/methodik_und_lessons_learned.md](../concepts/methodik_und_lessons_learned.md) §4.3
