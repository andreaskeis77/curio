# Project State

**Stand:** 2026-05-09
**Aktive Tranche:** M2 — Extraction & Proposal Ingest (abgeschlossen, Push ausstehend)
**Aktuelle Version:** 0.3.0-proposal-ingest (in Vorbereitung)
**Repository:** https://github.com/andreaskeis77/curio

Dieses Dokument ist die **lebende Statusübersicht** des Projekts. Es wird nach jeder relevanten Tranche aktualisiert.

---

## Was gerade gilt

- **Phase:** M2 abgeschlossen. Extraction-Pipeline (HTML/PDF/MD/Text/Data), LLM-Client-Wrapper mit Mock-Default, Prompt-Registry, Proposal-Store, Quarantäne, Prompt-Injection-Heuristik.
- **Was es schon gibt:** Repo-Struktur, kanonische Dokumente, ADRs 0001–0011, ROADMAP, Konzept-Dokumente, CLI mit `registry`, `capture`, `sources`, `extract`, `ingest`, `proposal`, `quarantine`. Path-Abstraktion, ID-Generator, SHA-256 Hashing, YAML-Manifests, SQLite v2, drei LLM-Provider-Adapter (mock/anthropic/openai), Prompt `ingest_v0_1`, drei Test-Fixtures (UNESCO HTML, Pacojet MD, Prompt-Injection MD).
- **Was es noch nicht gibt:** Wiki-Seitentypen mit Frontmatter-Templates, Atomic Publish nach `wiki/`, Review-Workflow (approve/reject), Claim-Registry, Sucharchitektur, Web-UI, VPS-Deployment.
- **LLM-Modus:** Mock-Default. Anthropic-/OpenAI-Adapter implementiert, aber im MVP per Default deaktiviert (kein API-Key, kein Cost-Risiko).
- **Pilotbereiche im Fokus:** UNESCO und Pacojet (Fixtures vorhanden, M3 nutzt sie für Wiki-Generation).

## Letzte abgeschlossene Tranche

**M2 — Extraction & Proposal Ingest**

Deliverables:

- **ADR-0010** LLM-Client-Wrapper-Implementierung (Provider-Adapter, Pydantic-Validation, Run Evidence).
- **ADR-0011** Extraction-Strategie und Fallbacks (Format-Adapter pro Source-Type).
- **SQLite-Schema v2** (Migration 0002): `extractions`, `agent_prompts`, `ingest_runs`, `proposals`, `quarantine_cases` mit Foreign Keys auf `sources`.
- **Extraction-Adapter** für HTML (trafilatura 2.0), PDF (pypdf 6.10), Markdown/Text (Passthrough), Data (JSON pretty / CSV-wrap). Output: `extracted/<source_id>.md` mit YAML-Frontmatter.
- **Pipeline** `extract_source()` mit Status-Statemaschine, atomic write, Idempotenz.
- **LLM-Client-Wrapper** mit Provider-Factory (mock/anthropic/openai), Retry-Logic, Run Evidence, Schema-Validation via Pydantic.
- **Mock-Provider** mit Fixture-Loader und deterministischem Default-Output.
- **Prompt-Registry** mit Datei-basierten Prompts, Body-Hash, Frontmatter-Parser, README-Skip.
- **Pydantic-Schemas** `IngestProposalV1` mit `ProposedPage`, `HardFact`, `RiskNote`, `FreshnessRecommendation`.
- **System-Prompts** `source_trust.md`, `output_discipline.md`.
- **Agent-Prompt** `ingest_v0_1.md` mit Untrusted-Source-Pattern und Heuristiken pro Wissensart.
- **Prompt-Injection-Heuristik** (`injection_findings`) mit 6 Patterns.
- **Proposal-Store** mit `proposal.yaml`, `summary.md`, `risk_notes.md`, `run_evidence.yaml` pro Run.
- **Proposal-Repository** und **Quarantine-Repository**.
- **Pipeline** `ingest_source()` mit Pre-LLM-Injection-Scan, Quarantäne-Logik, Status-Updates.
- **CLI**: `extract`, `ingest`, `proposal list/show`, `quarantine list`. Quarantäne liefert exit code 2.
- **Fixtures** unter `tests/fixtures/sources/`: UNESCO-Alhambra-HTML, Pacojet-Sorbet-MD, Prompt-Injection-MD.
- **Tests**: 47 neue (extraction adapters + pipeline, agents schema/registry/client/injection/providers, proposals ingest, CLI M2). Gesamttests: **143 grün**.

Akzeptanzkriterien M2 (alle erfüllt):

- UNESCO-HTML-Fixture wird durch trafilatura sauber zu Markdown extrahiert.
- Pacojet-Notiz-Fixture wird per Passthrough als Markdown übernommen.
- Mock-LLM erzeugt validiertes Pydantic-Proposal aus Source + Extracted Content.
- Prompt-Injection-Fixture (`Ignore all previous instructions`) wird VOR LLM-Call erkannt, in Quarantäne überführt, kein Wiki-Schreibvorgang, kein Proposal.
- Replay desselben Source/Prompt im Mock-Modus liefert deterministischen strukturellen Output.
- Token-/Cost-Logging in `ingest_runs.token_usage_json` vorhanden.
- Agent schreibt unter keinen Umständen nach `wiki/` (Test verifiziert).
- 4/4 Quality Gates grün (pytest, ruff check, ruff format, secret-scan).

## Aktive Tranche

Keine. Nächste: **M3 — Review & Publish**.

## Offene rote Pfade

Keine.

## Bekannte Einschränkungen

- Keine Auto-Approval und kein `wiki/`-Schreib in M2 — Proposals bleiben `pending`.
- Anthropic/OpenAI-Provider sind implementiert, aber nicht gegen reale APIs in Tests gelaufen (würde Keys + Cost erfordern). Mock ist Default.
- PDF-Extraktion mit minimalem PDF kann je nach pypdf-Version variieren (Test toleriert `extracted` oder `failed`).
- Prompt-Injection-Heuristik ist regex-basiert — keine semantische Erkennung. Reicht als Vorwarn-Stufe; LLM-Pattern-Robustness liegt zusätzlich am Prompt-Design.
- Extracted-Files überschreiben sich bei Re-Extract — bewusst, da regenerierbar. `extractions`-Tabelle hält Run-Historie.

## Aktuelle Umgebung

| Komponente | Stand |
|---|---|
| Python | 3.11+ (getestet auf 3.12) |
| Lint | ruff 0.5+ — alles grün |
| Test | pytest 8.0+ — 143 Tests grün |
| Plattform | Windows 11 Pro (Dev), später Windows VPS |
| LLM Provider | mock (Default) / anthropic / openai |
| Registry | SQLite v2 (9 Tabellen) |
| Web UI | nicht vorhanden (kommt in M5) |
| Dependencies neu in M2 | trafilatura 2.0, pypdf 6.10, pydantic 2.13 |

## Nächste Tranche: M3 — Review & Publish

Geplante Deliverables (laut ROADMAP):

- CLI: `proposal approve <id>`, `proposal reject <id>`, `proposal request-changes <id>`.
- Wiki-Seitentyp-Templates (topic, place, person, recipe, method, experiment, product_research, source, collection, question, event).
- Frontmatter-Schema-Validierung.
- Atomic Write nach `wiki/`: temp file → fsync → atomic rename.
- Git-Auto-Commit nach Approval mit klarer Message-Convention.
- Claim-Registry minimal (nur harte Fakten).
- Backlinks-Berechnung.
- Source-Page-Generierung.
- Lint-Pre-Review-Check.
- ADR-0012 Atomic Writes und Git-Commit-Strategie.
- ADR-0013 Claim-Provenienz-Modell.

## Zuletzt aktualisiert

- 2026-05-08 — initial (T0.1 abgeschlossen).
- 2026-05-08 — M1 Registry Spine abgeschlossen.
- 2026-05-09 — M2 Extraction & Proposal Ingest abgeschlossen.

## Wie dieses Dokument zu pflegen ist

Nach jeder abgeschlossenen Tranche:

1. „Letzte abgeschlossene Tranche" aktualisieren.
2. „Aktive Tranche" auf nächste Phase setzen.
3. „Offene rote Pfade" prüfen und ggf. schließen.
4. „Aktuelle Umgebung" aktualisieren.
5. „Zuletzt aktualisiert" mit ISO-Datum erweitern.
6. Bei Architekturwirkung: ARD und/oder ADRs aktualisieren.
7. Bei Methodikänderung: ENGINEERING_MANIFEST oder WORKING_AGREEMENT aktualisieren.
