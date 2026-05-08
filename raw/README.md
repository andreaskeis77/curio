# raw/ — Immutable Raw Source Store

Dieser Ordner enthält **unveränderte Snapshots** aller erfassten Quellen.

## Regeln

- **Niemals überschreiben.** Erneuter Abruf einer URL erzeugt einen neuen Snapshot.
- **Niemals löschen** ohne Backup und Dokumentation.
- **Niemals committen** außer als explizit unkritische Beispiel-Fixtures.
- Manifest und Hash gehen immer mit.

## Pfad-Schema

```text
raw/<source_type>/<YYYY>/<MM>/<DD>/<source_id>/
  original.<ext>           # unveränderter Quellinhalt
  metadata.yaml            # Manifest: id, title, source_type, ...
  content.sha256           # Hash zur Verifikation
```

## Source Types

- `inbox/` — frisch erfasst, noch nicht klassifiziert
- `web/` — Webseiten (HTML)
- `pdf/` — PDFs
- `screenshots/` — Bildschirmfotos
- `notes/` — eigene Notizen
- `data/` — strukturierte Daten (CSV, JSON)

## Git-Behandlung

`raw/**/*` ist in `.gitignore` ausgeschlossen, außer:

- READMEs (wie diese)
- Explizit unkritische Beispiel-Fixtures (in `tests/fixtures/sources/`)

## Verweise

- [docs/SOURCE_POLICY.md](../docs/SOURCE_POLICY.md)
- [docs/adr/ADR-0002-immutable-raw-sources.md](../docs/adr/ADR-0002-immutable-raw-sources.md)
