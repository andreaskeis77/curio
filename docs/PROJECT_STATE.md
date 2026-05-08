# Project State

**Stand:** 2026-05-08
**Aktive Tranche:** M1 — Registry Spine (abgeschlossen, Push ausstehend)
**Aktuelle Version:** 0.2.0-registry-spine (in Vorbereitung)
**Repository:** https://github.com/andreaskeis77/curio

Dieses Dokument ist die **lebende Statusübersicht** des Projekts. Es wird nach jeder relevanten Tranche aktualisiert.

---

## Was gerade gilt

- **Phase:** M1 abgeschlossen. SQLite-Registry, Source-Capture-Pipeline, Manifest-IO, Duplicate Detection, Source Policy Heuristik.
- **Was es schon gibt:** Repo-Struktur, kanonische Dokumente, ADRs 0001–0009, ROADMAP, Konzept-Dokumente, CLI mit `registry init/check`, `capture url/file/note`, `sources list/show/inbox`. Path-Abstraktion, ID-Generator, SHA-256 Hashing, YAML-Manifests, SQLite v1.
- **Was es noch nicht gibt:** Extraction (HTML/PDF/Markdown), LLM-Ingest, Proposal-Store, Wiki-Seitentypen, Web-UI, VPS-Deployment.
- **LLM-Modus:** Mock-Default. Echte LLM-Calls erst ab M2.
- **Pilotbereiche im Fokus:** UNESCO und Pacojet (geplant für M2/M3).

## Letzte abgeschlossene Tranche

**M1 — Registry Spine**

Deliverables:

- ADR-0009 Registry-Schema-Versionierung.
- SQLite-Schema v1: `sources`, `source_snapshots`, `jobs`, `schema_meta`.
- Migration-Runner (idempotent, ``CREATE IF NOT EXISTS``-basiert).
- Source-Domain-Modell mit Enums (`SourceType`, `AccessType`, `CopyrightRisk`, `Reliability`, `SourceStatus`).
- Hashing-Utilities (SHA-256 für Bytes und Files, chunked).
- Source-Pfad-Schema: `raw/<type>/<YYYY>/<MM>/<DD>/<source_id>/`.
- YAML-Manifest-Reader/Writer mit atomic write.
- Source-Policy-Heuristik (Domain-basiert: official, expert, journalistic, paywall).
- Capture-Adapter: `capture_url` (urllib + mockbarer fetcher), `capture_file` (shutil.copy2), `capture_note` (Markdown).
- Duplicate Detection über Hash und URL.
- CLI: `registry init/check`, `capture url/file/note`, `sources list/show/inbox`.
- 39 neue Tests (Unit + Contract + Integration). Gesamttests: **96 grün**.

Akzeptanzkriterien M1 (alle erfüllt):

- 3+ Beispielquellen wurden im Smoke-Test erfasst (2 Notizen, 1 Datei).
- Jede Quelle hat Manifest, Hash, `why_interesting`.
- Doppelte Quelle (gleicher Hash) wird erkannt und blockiert (exit 2).
- `--allow-duplicate` erlaubt bewusst doppelte Erfassung.
- `curiosity registry check` ist grün.
- Fresh-State und Evolved-State funktionieren (durch Tests verifiziert).

## Aktive Tranche

Keine. Nächste: **M2 — Extraction & Proposal Ingest**.

## Offene rote Pfade

Keine.

## Bekannte Einschränkungen

- Extraction-Pipeline fehlt — `extracted/` bleibt leer bis M2.
- Echter HTTP-Capture in Production möglich, aber kein Stress-Test gegen reale Webseiten durchgeführt.
- Atomic-Write für `_persist`: Manifest-File wird vor Registry-Insert geschrieben. Bei DB-Fehler kann ein Manifest ohne DB-Eintrag auf der Platte verbleiben (orphan). Pragmatisch akzeptiert für M1; künftig durch `registry rebuild-from-manifests` aufräumbar.
- Snapshots-Tabelle (`source_snapshots`) existiert, wird aber noch nicht aktiv beschrieben — kommt in M2 wenn Re-Capture wichtig wird.

## Aktuelle Umgebung

| Komponente | Stand |
|---|---|
| Python | 3.11+ (getestet auf 3.12) |
| Lint | ruff 0.5+ — alles grün |
| Test | pytest 8.0+ — 96 Tests grün |
| Plattform | Windows 11 Pro (Dev), später Windows VPS |
| LLM Provider | Mock (M1 nutzt noch keine LLM-Calls) |
| Registry | SQLite v1 (Tabellen: schema_meta, sources, source_snapshots, jobs) |
| Web UI | nicht vorhanden (kommt in M5) |

## Nächste Tranche: M2 — Extraction & Proposal Ingest

Geplante Deliverables:

- Extraction-Pipeline: HTML (trafilatura/readability), Markdown (passthrough), PDF-light.
- `extracted/<source_id>.md` mit Metadaten-Header.
- LLM-Client-Wrapper (ADR-0007) mit Mock-Modus default.
- Prompt Registry, erstes Prompt: `ingest_v0_1`.
- Proposal Store mit Schema-Validation.
- CLI: `extract <source_id>`, `ingest <source_id>`.
- Prompt-Injection-Schutz, Quarantäne.
- Golden Tests mit Fixtures (UNESCO-short, Pacojet-recipe-short, prompt-injection).
- ADR-0010 (LLM-Client-Wrapper-Implementierung) und ADR-0011 (Extraction-Strategie und Fallbacks).

## Zuletzt aktualisiert

- 2026-05-08 — initial (T0.1 abgeschlossen).
- 2026-05-08 — M1 Registry Spine abgeschlossen.

## Wie dieses Dokument zu pflegen ist

Nach jeder abgeschlossenen Tranche:

1. „Letzte abgeschlossene Tranche" aktualisieren.
2. „Aktive Tranche" auf nächste Phase setzen.
3. „Offene rote Pfade" prüfen und ggf. schließen.
4. „Aktuelle Umgebung" aktualisieren.
5. „Zuletzt aktualisiert" mit ISO-Datum erweitern.
6. Bei Architekturwirkung: ARD und/oder ADRs aktualisieren.
7. Bei Methodikänderung: ENGINEERING_MANIFEST oder WORKING_AGREEMENT aktualisieren.
