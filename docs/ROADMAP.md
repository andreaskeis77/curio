# Curiosity Wiki — Roadmap

**Stand:** 2026-05-09
**Aktuelle Tranche:** M6 abgeschlossen (Code-Seite); VPS-Setup und Restore-Drill bei Andreas
**Nächste Tranche:** M7 First Update Scout
**Kanonisches Statusdokument:** [PROJECT_STATE.md](PROJECT_STATE.md)

Diese Roadmap ist methodikgetrieben, nicht featuregetrieben. Jede Phase hat klare Deliverables, Akzeptanzkriterien und eine Definition, was bewusst _nicht_ enthalten ist. Reihenfolge ist verbindlich. Phasen werden nicht parallelisiert, außer das Manifest erlaubt es ausdrücklich.

## Leitlinien

1. **MVP ist nicht das perfekte Wiki.** Der MVP ist die kleinste robuste Pipeline, die aus einer Quelle einen überprüfbaren, verlinkten, versionierten Wiki-Beitrag erzeugt.
2. **Robustheit vor Tempo.** Datenintegrität, Reproduzierbarkeit und Rebuildbarkeit haben Vorrang vor Featurebreite.
3. **Methodik vor Implementierung.** Architekturentscheidungen, Manifeste und Tests entstehen vor dem Code, der davon abhängt.
4. **Read-only zuerst.** VPS-Deployment beginnt read-only. Schreibrechte für Agenten kommen erst, wenn Review, Backup und Rollback stabil sind.
5. **Keine zu breiten Tranchen.** Eine Tranche darf nicht gleichzeitig Registry-Schema, Agent-Prompt und UI-Layout ändern.

---

## Phasenübersicht

| Phase | Titel | Zielzustand | Status |
|---|---|---|---|
| **T0.1** | Method & Architecture Baseline | Repo, Docs, ADRs, Minimal-CLI, pytest grün | abgeschlossen |
| **M1** | Registry Spine | Source Capture mit SQLite Registry, Hashing, Manifests | abgeschlossen |
| **M2** | Extraction & Proposal Ingest | Extracted Markdown, Mock-LLM-Proposals, Proposal Schema | abgeschlossen |
| **M3** | Review & Publish | Review-CLI, Atomic Writes, Wiki-Seitentypen, Claim-Registry | abgeschlossen |
| **M4** | Browse, Search, Lint | SQLite FTS, Lesepfade, Lint-Report, Golden Questions | abgeschlossen |
| **M5** | Local Web UI | Backend API, Page Reader, Source Drawer, Mobile Layout | abgeschlossen |
| **M6** | VPS Read-only Preview | Publish Bundle, Cloudflare Tunnel, Backup, Health, Rollback | **Code abgeschlossen, VPS-Setup offen** |
| **M7** | First Update Scout | Kontrollierte Aktualitätslogik für genau einen Bereich | offen |

Nach M7: Phase A (Robustheit), Phase B (Produkttests), Phase C (Haute Couture), Phase D (Motorsport/ESC/Bond), Phase E (Hybrid Search), Phase F (Mobile Polish/PWA).

---

## T0.1 — Method & Architecture Baseline

**Ziel:** Das Projekt ist methodisch anschlussfähig, bevor Code wächst. Jede zukünftige Tranche kann auf dokumentierten Entscheidungen aufsetzen.

### Deliverables

- Repo-Struktur (`docs/`, `src/`, `tests/`, `tools/`, `scripts/`, `raw/`, `extracted/`, `wiki/`, `proposals/`, `read_models/`, `data/`).
- 17 kanonische Dokumente in `docs/`.
- ADRs 0001–0008.
- Konzept-Dokumente unter `docs/concepts/`.
- `pyproject.toml` mit Click-CLI, ruff, pytest.
- Minimaler CLI-Skelett `curiosity` mit `--help`, `--version`, `paths`-Befehl.
- Path-Abstraktion (`curiosity_wiki.paths`).
- ID-Generator (`curiosity_wiki.ids`) mit ULID-ähnlichem Format.
- `.env.example`, `.gitignore`, `.gitattributes`.
- PR-Template und Branch-Protection-Config.
- Vault-Stub-Struktur mit READMEs (raw/extracted/wiki/proposals/read_models).
- PowerShell-Scripts: `dev.ps1`, `test.ps1`, `lint.ps1`.
- Quality-Gate-Skript `tools/run_quality_gates.py`.

### Akzeptanzkriterien

- `git status --short` ist nach Commit sauber.
- `python -m pytest -q` ist grün.
- `python -m ruff check src tests tools` ist grün.
- `python -m curiosity_wiki --help` zeigt Top-Level-Commands.
- `python -m curiosity_wiki --version` gibt Version aus.
- `python -m curiosity_wiki paths` zeigt erkannte Vault-Pfade.
- `docs/INDEX.md` listet alle kanonischen Dokumente.
- `docs/PROJECT_STATE.md` beschreibt aktuellen Stand und nächste Tranche.

### Bewusst _nicht_ in T0.1

- Echter LLM-Ingest.
- Web-UI.
- VPS-Deployment.
- Echte Capture-/Extraction-Logik.
- Produkttests, Haute Couture, Motorsport.
- SQLite-Schema-Erstellung (kommt in M1).

---

## M1 — Registry Spine

**Ziel:** Quellen können robust abgelegt und in der Registry registriert werden. Die Registry wird zur einzigen Quelle der Wahrheit für operative Zustände.

### Deliverables

- SQLite-Schema v1: `sources`, `source_snapshots`, `extractions` (leer), `pages` (leer), `claims` (leer), `proposals` (leer), `ingest_runs`, `lint_runs`, `lint_findings`.
- Migration-Runner in `src/curiosity_wiki/registry/migrations/`.
- Source-Manifest-Schema (YAML-Frontmatter).
- ID-Generator-Strategie (ULID + Timestamp-Präfix für Sources).
- SHA-256 Hashing.
- CLI: `curiosity capture url <URL>`, `curiosity capture file <PATH>`, `curiosity capture note <TEXT>`.
- CLI: `curiosity sources list`, `curiosity sources show <id>`.
- CLI: `curiosity registry init`, `curiosity registry check`.
- Duplicate Detection v1 (gleiche URL oder gleicher Hash → Warnung).
- Source Policy Felder: `access`, `copyright_risk`, `llm_allowed`, `reliability`.
- Inbox-Report (`curiosity sources inbox`).
- Tests: Unit für IDs, Hashing, Manifest-Parsing. Contract für CLI-Commands. Integration für End-to-End Capture.
- ADR-0009: Registry-Schema-Versionierung.

### Akzeptanzkriterien

- 5 Beispielquellen können erfasst werden (3 URLs, 2 Dateien).
- Jede Quelle hat Manifest, Hash, `why_interesting`.
- Doppelte URL/Hash wird erkannt und gewarnt.
- `curiosity registry check` ist grün.
- Fresh-State und Evolved-State Tests laufen.

### Bewusst _nicht_ in M1

- Extraktion (kommt in M2).
- LLM-Aufrufe (kommt in M2).
- Wiki-Seiten (kommt in M3).

---

## M2 — Extraction & Proposal Ingest

**Ziel:** Quellen werden extrahiert, und ein LLM erzeugt einen Vorschlag — niemals direkt eine Wiki-Seite.

### Deliverables

- Extraction-Pipeline: HTML (trafilatura/readability), Markdown (passthrough), Text, PDF-light (pypdf).
- `extracted/<source_id>.md` mit Metadaten-Header.
- Extraction-Statusmaschine: `captured` → `extracted` → `extraction_failed`.
- Prompt Registry: `prompts/agents/ingest.md` v1, mit Prompt-ID und Hash.
- LLM-Client-Abstraktion mit Mock-Modus (default), Anthropic, OpenAI.
- Output-Schema-Validierung (JSON-Schema oder Pydantic).
- Proposal-Store: `proposals/<run_id>/proposal.yaml`, `summary.md`, `patch.diff`, `risk_notes.md`.
- Run Evidence: `prompt_id`, `prompt_hash`, `model`, `temperature`, `token_usage`.
- CLI: `curiosity extract <source_id>`, `curiosity ingest <source_id>`.
- Prompt-Injection-Schutz: Quellen-Inhalt klar als untrusted markiert.
- Quarantäne bei verdächtigen Quellen.
- Tests: Unit für Extraktion. Golden Tests mit Fixtures (UNESCO-short, Pacojet-recipe-short, prompt-injection). Mock-LLM-Tests.
- ADR-0010: Prompt Registry und LLM-Client-Wrapper.
- ADR-0011: Extraction-Strategie und Fallbacks.

### Akzeptanzkriterien

- UNESCO-Fixture erzeugt plausibles Proposal.
- Pacojet-Fixture erzeugt Rezept-/Methoden-Vorschlag.
- Prompt-Injection-Fixture erzeugt Quarantäne-Eintrag, kein Proposal-Schreibe in `wiki/`.
- Agent schreibt nicht nach `wiki/`.
- Replay desselben Sources mit gleicher Prompt-ID erzeugt deterministischen Output (Mock-Modus).
- Token-/Cost-Logging vorhanden.

### Bewusst _nicht_ in M2

- Review-Workflow (M3).
- Publish nach `wiki/` (M3).
- Web-UI (M5).

---

## M3 — Review & Publish

**Ziel:** Vorschläge können geprüft, akzeptiert oder verworfen werden. Akzeptierte Vorschläge werden atomar nach `wiki/` geschrieben.

### Deliverables

- CLI: `curiosity proposal list`, `proposal show <id>`, `proposal approve <id>`, `proposal reject <id>`, `proposal request-changes <id>`.
- Wiki-Seitentyp-Templates (topic, place, person, recipe, method, experiment, product_research, source, collection, question, event).
- Frontmatter-Schema-Validierung.
- Atomic Write: temp file → fsync → atomic rename.
- Git-Auto-Commit nach Approval (mit klarer Commit-Message-Konvention).
- Claim-Registry minimal (nur harte Fakten: Zahlen, Datumsangaben, Preise, Spezifikationen).
- Backlinks-Berechnung.
- Source-Page-Generierung.
- Lint-Pre-Review-Check.
- ADR-0012: Atomic Writes und Git-Commit-Strategie.
- ADR-0013: Claim-Provenienz-Modell.

### Akzeptanzkriterien

- Proposal kann angenommen, verworfen, geändert werden.
- Annahme erzeugt saubere Markdown-Seiten mit gültigem Frontmatter.
- Git-Historie zeigt jede Änderung mit klarer Message.
- Fehler beim Publish lässt alte Dateien intakt (atomic).
- Source-Verweise sind nach Publish in der Registry verlinkt.
- Claim ohne Source wird beim Lint gefunden.

### Bewusst _nicht_ in M3

- Web-Review-UI (M5).
- Search (M4).
- Browse-Funktionen (M4).

---

## M4 — Browse, Search, Lint

**Ziel:** Das Wiki ist nutzbar, durchsuchbar und pflegbar.

### Deliverables

- SQLite FTS5 Index über Wiki-Seiten.
- CLI: `curiosity search "<query>"`, `curiosity browse --random`, `curiosity browse --topic <name>`, `curiosity browse --collection <name>`.
- Lint-Regeln (mindestens 12): fehlendes Frontmatter, kaputter Wikilink, fehlende Quellen, Claim ohne Source, orphan page, duplicate title, alte volatile Seite, Produktseite ohne `last_checked`, Source ohne `why_interesting`, Proposal ohne Diff, Wiki-Seite > 2500 Wörter, Doppel-Titel/Aliases.
- `curiosity lint` gibt Markdown-Report aus, schreibt nach `docs/_ops/lint_reports/`.
- Open-Questions-Aggregation.
- Freshness-Dashboard-Daten (`review_after` überschritten).
- Golden Questions: `eval/golden-questions.yaml` mit ersten 10 Fragen.
- `curiosity eval golden` läuft die Fragen und prüft Output-Struktur.
- Index-Rebuild aus Wiki-Markdown.
- ADR-0014: Sucharchitektur (Stufenmodell).

### Akzeptanzkriterien

- Suche findet Seiten nach Titel, Frontmatter, Volltext.
- Browse erzeugt sinnvolle Lesepfade.
- Lint findet absichtlich eingebaute Fehler.
- Golden Questions laufen und prüfen Erwartungen.
- Index ist rebuildbar.

### Bewusst _nicht_ in M4

- Embeddings/Vector Search (Phase E).
- Web-UI (M5).
- Hybrid Retrieval (Phase E).

---

## M5 — Local Web UI

**Ziel:** Lesen und Schmökern funktionieren am Laptop und Smartphone.

### Deliverables

- FastAPI-Backend mit Endpunkten: `/api/health`, `/api/pages`, `/api/pages/{id}`, `/api/sources`, `/api/search`, `/api/browse/random-walk`, `/api/proposals` (read-only im MVP), `/api/lint/report/latest`.
- Read-Models: `read_models/site_index.json`, `graph.json`, `search_documents.jsonl`, `freshness_dashboard.json`, `page_cards.json`, `mobile_nav.json`.
- Server-rendered HTML mit Jinja2 (kein SPA im MVP).
- Optional htmx für kleine Interaktionen.
- Home Dashboard: Weiterlesen, Heute interessant, Offene Fragen, Needs Review, Veraltet, Random Walk.
- Page Reader mit Source-Drawer, Backlinks, Freshness-Badges, Confidence-Badge.
- Mobile-First Layout (< 768px), Tablet (768–1024px), Desktop (> 1024px).
- Search-Page.
- Source-Page mit Raw-Snapshot-Link.
- Accessibility-Basics: semantic HTML, Tastaturnavigation, Kontrast, `prefers-reduced-motion`.
- ADR-0015: Web-Stack-Entscheidung (FastAPI + Jinja2 vs. SPA).
- ADR-0016: Read-Model-Strategie.

### Akzeptanzkriterien

- Home lädt lokal auf 127.0.0.1.
- UNESCO- und Pacojet-Beispielseiten lesbar.
- Mobile Smoke per Browser DevTools grün.
- UI liest aus Read Models und Wiki, nicht direkt aus Raw.
- Suche und Browse funktionieren.
- `/api/health` ist grün.
- Quellen, Freshness, Confidence sichtbar.

### Bewusst _nicht_ in M5

- VPS-Deployment (M6).
- Schreibfunktionen in der UI (später, optional).
- PWA / Offline-Modus (Phase F).

---

## M6 — VPS Read-only Preview

**Ziel:** Kontrolliertes read-only Deployment auf Windows-VPS.

### Deliverables

- Publish-Bundle-Builder: Filtert private Raw Sources, packt nur freigegebene Wiki-Seiten + Read Models + nicht-private Source-Metadaten.
- Deployment-Skript `scripts/deploy-windows-vps.ps1`: Preflight, Backup, Deploy, Migration, Index-Rebuild, Service-Restart, Healthcheck, Rollback.
- Windows-Service-Konfiguration via WinSW oder NSSM.
- Reverse Proxy: Caddy oder Cloudflare Tunnel für Web.
- Tailscale für Admin-Zugang (RDP nur via Tailscale).
- Windows-Firewall-Baseline (eingehend nur, was nötig ist).
- Backup-Skript: Repo-Bundle, Raw-Blobs (lokal!), SQLite-Registry, Manifest, Hash.
- Backup-Task via Windows Scheduled Task.
- Restore-Skript und Restore-Drill.
- Health-Endpoint: `/healthz` (liveness), `/healthz/deep` (registry, wiki path, read models).
- Release-Tagging-Konvention.
- Release-Notes-Template.
- ADR-0017: VPS-Deployment-Modell.
- ADR-0018: Backup/Restore-Strategie.

### Akzeptanzkriterien

- VPS zeigt read-only Wiki über Cloudflare Tunnel.
- Service startet automatisch nach Reboot.
- Backup wird vor jedem Deployment erzeugt.
- Rollback dokumentiert und mindestens einmal getestet.
- Restore-Drill auf leerem Verzeichnis erfolgreich.
- Keine privaten Raw Sources im Publish-Bundle.
- Secret-Scan vor Publish ist grün.

### Bewusst _nicht_ in M6

- Schreibfunktionen auf VPS.
- Login/Auth für Admin-Funktionen (Phase D4).
- Multiuser.

---

## M7 — First Update Scout

**Ziel:** Kontrollierte Aktualitätslogik für genau einen Bereich.

### Deliverables

- Scout-Definition als YAML: erlaubte Quellen, Frequenz, Output-Format.
- Scheduler (lokal, nicht auf VPS): Scheduled Task / cron.
- Update-Proposal-Erzeugung statt Direkt-Änderung.
- Freshness-Dashboard erweitert: Status pro Bereich.
- Quarantäne bei Unsicherheit.
- Scout-Logs in `docs/_ops/ingest_runs/`.
- ADR-0019: Update-Scout-Modell.

**Empfohlener erster Scout:** UNESCO oder eine kleine Produktkategorie (z.B. Powerbanks). Nicht beide gleichzeitig.

### Akzeptanzkriterien

- Scout schreibt Proposals, nicht direkt nach Wiki.
- Wiki wird nicht automatisch überschrieben.
- Freshness-Dashboard zeigt Status pro Quelle.
- Scout-Ausfall blockiert das System nicht.

---

## Phasen nach dem MVP

### Phase A — Robustheit vor Features

- Registry-Rebuild aus Markdown/Manifests.
- Backup/Restore-Test als CI-Job.
- Mehr Lint-Regeln (Ziel: 25+).
- Bessere Proposal-Diffs.
- Claim-Markierung verbessern.
- Windows-Kompatibilität härten.

### Phase B — Produkttests und Freshness

- Product-Research-Templates.
- `review_after`-Dashboard.
- Update Scout für eine Produktkategorie.
- Shortlists und Vergleichstabellen.

### Phase C — Haute Couture (narratives Kulturwissen)

- Personen-, Marken-, Begriffsseiten.
- Zeitachsen.
- Essay-/Dossier-Seiten.
- Link-Agent verbessern.

### Phase D — Motorsport / ESC / James Bond

- Periodisches Ereigniswissen.
- Strukturierte Datenimporte (CSV/JSON).
- Jahrgangsseiten und Timelines.

### Phase E — Hybrid Search und Query Agent

- SQLite FTS produktiv.
- Embeddings über Wiki-Abschnitte.
- Hybrid Retrieval.
- Query-Antworten mit Quellenbezug.
- Golden Questions ausbauen.

### Phase F — Mobile Polish / PWA

- Bessere mobile Navigation.
- Offline-Lesemodus.
- „Später lesen".
- Lesefortschritt.
- Share-to-Capture.
- PWA optional.

---

## Methodikgetriebene Reihenfolge

Warum genau diese Reihenfolge?

- **UI ohne stabile Datenmodelle** erzeugt später Refactoring → Daten zuerst.
- **LLM-Ingest ohne Review** erzeugt Qualitätsrisiko → Review-Workflow vor breitem Ingest.
- **Suche ohne saubere Metadaten** bleibt oberflächlich → Frontmatter-Disziplin vor Suche.
- **Deployment ohne Backup/Restore** ist nicht produktionsreif → Backup vor Public-Web.
- **Update Scouts ohne Freshness-Dashboard** sind blind → Dashboard vor Automation.

---

## Definition of Done für jede Phase

Eine Phase ist erst abgeschlossen, wenn:

- Akzeptanzkriterien erfüllt sind.
- Tests grün (Unit, Contract, Integration, relevant für Phase).
- Lint/Format grün.
- Doku aktualisiert (PROJECT_STATE, ARD/ADR bei Architekturwirkung, RUNBOOK bei Betriebswirkung).
- Bei UI-Änderungen: Mobile geprüft.
- Bei Prompt-Änderungen: Golden Questions ≥ Baseline.
- Keine Secrets im Diff.
- Windows-Kompatibilität geprüft.
- Handoff-Dokument aktualisiert.

---

## Risiken pro Phase

| Phase | Hauptrisiko | Gegenmaßnahme |
|---|---|---|
| T0.1 | Doku-Inflation ohne Code | INDEX.md mit klarer Hierarchie, jede Datei hat Zweck |
| M1 | SQLite-Schema zu groß starten | Nur Pflichtfelder, Erweiterung in eigener Tranche |
| M2 | LLM-Output unvorhersehbar | Mock-Modus default, JSON-Schema-Validierung, Fixtures |
| M3 | Atomic Writes scheitern auf Windows | Früh testen, fsync + rename, Tests auf Windows |
| M4 | FTS-Index inkonsistent | Rebuild-Strategie, Index als generated, nicht primär |
| M5 | UI explodiert in Komplexität | Server-rendered, kein SPA, klares Feature-Set |
| M6 | Private Raw Sources im Bundle | Filter-Whitelist, Secret Scan, Manueller Pre-Push-Check |
| M7 | Scout-Kosten/Halluzinationen | Quarantäne, Mock-Modus, klare Quell-Whitelist |

---

## Weiterführende Dokumente

- [PROJECT_STATE.md](PROJECT_STATE.md) — aktueller Stand
- [ARCHITECTURE_REQUIREMENTS_DOSSIER.md](ARCHITECTURE_REQUIREMENTS_DOSSIER.md) — Architektur
- [ENGINEERING_MANIFEST.md](ENGINEERING_MANIFEST.md) — Engineering-Regeln
- [TEST_STRATEGY.md](TEST_STRATEGY.md) — Teststrategie
- [VALIDATION_PROTOCOL.md](VALIDATION_PROTOCOL.md) — Validierungsleiter
- [RELEASE_PROCESS.md](RELEASE_PROCESS.md) — Releases und Versionen
- [adr/](adr/) — Architecture Decision Records
