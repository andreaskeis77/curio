# docs/ — Index

Navigations- und Hierarchie-Übersicht aller kanonischen Dokumente. Bei Konflikt zwischen Dokumenten gilt die **Kanon-Hierarchie**: ARD > ADRs > Manifest > sonstige Dokumente > Handoffs.

## Was ist kanonisch?

| Dokument | Rolle |
|---|---|
| [ARCHITECTURE_REQUIREMENTS_DOSSIER.md](ARCHITECTURE_REQUIREMENTS_DOSSIER.md) | **Architekturwahrheit.** Layer, Runtime, Persistenz, Schnittstellen, NFRs. |
| [ENGINEERING_MANIFEST.md](ENGINEERING_MANIFEST.md) | **Verbindliche Engineering-Regeln.** Prinzipien, Definition of Done. |
| [adr/](adr/) | **Architektur-Entscheidungen.** Datierte, nummerierte ADRs. |
| [PROJECT_STATE.md](PROJECT_STATE.md) | **Aktueller Stand.** Lebende Datei, wird pro Tranche aktualisiert. |
| [ROADMAP.md](ROADMAP.md) | **Phasenplan.** T0.1 bis M7 und darüber hinaus. |

## Methodik und Zusammenarbeit

| Dokument | Rolle |
|---|---|
| [WORKING_AGREEMENT.md](WORKING_AGREEMENT.md) | Zusammenarbeit Andreas ↔ Assistent. Phasenmodus, Output-Format. |
| [DELIVERY_PROTOCOL.md](DELIVERY_PROTOCOL.md) | Wie Tranchen umgesetzt, geprüft, angewendet werden. |
| [VALIDATION_PROTOCOL.md](VALIDATION_PROTOCOL.md) | 10-stufige Validierungsleiter, Fresh/Evolved State, Replay-Regeln. |
| [TEST_STRATEGY.md](TEST_STRATEGY.md) | Testschichten, Gates, Fixtures. |
| [RELEASE_PROCESS.md](RELEASE_PROCESS.md) | Tranche → RC → Release → Evidence → Baseline. |
| [LESSONS_LEARNED.md](LESSONS_LEARNED.md) | Fehlerklassen und methodische Konsequenzen. |

## Betrieb und Sicherheit

| Dokument | Rolle |
|---|---|
| [RUNBOOK.md](RUNBOOK.md) | Lokaler Betrieb, CLI, Backup, Restore, Fehlerdiagnose. |
| [SECURITY.md](SECURITY.md) | Secrets, lokale Daten, VPS-Zugang, Agent-Security. |
| [SOURCE_POLICY.md](SOURCE_POLICY.md) | Welche Quellen wie gespeichert werden dürfen. |

## Produkt und Inhalt

| Dokument | Rolle |
|---|---|
| [UI_UX_GUIDE.md](UI_UX_GUIDE.md) | Layout, mobile UX, Source Badges, Browse-Flows. |
| [PROMPT_REGISTRY.md](PROMPT_REGISTRY.md) | Prompt-IDs, Versionen, Zweck, Risiken. |
| [EVAL_STRATEGY.md](EVAL_STRATEGY.md) | Golden Questions, Fidelity Checks, Claim Checks. |

## Konzepte (historische Referenz)

| Dokument | Rolle |
|---|---|
| [concepts/feinkonzept.md](concepts/feinkonzept.md) | Synthese des ursprünglichen Feinkonzepts (2026-05-05). |
| [concepts/methodik_und_lessons_learned.md](concepts/methodik_und_lessons_learned.md) | Methodik aus capsule und new_nfl. |

Diese Dokumente sind nicht kanonisch. Bei Konflikt mit ARD/ADRs gelten ARD/ADRs.

## Operative Artefakte (lokal, nicht-kanonisch)

| Pfad | Inhalt |
|---|---|
| `_handoff/` | Übergabe-Artefakte zwischen Sessions. Nicht Architekturwahrheit. |
| `_ops/quality_gates/` | Logs aus Quality-Gate-Läufen. |
| `_ops/releases/` | Release-Evidence. |
| `_ops/lint_reports/` | Lint-Reports. |
| `_ops/ingest_runs/` | Ingest-Run-Logs. |
| `_ops/deployment_evidence/` | Deployment-Evidence. |
| `_ops/restore_drills/` | Restore-Drill-Logs. |

## Konvention

- **Kanonische Dokumente** haben keine Datumsangaben im Dateinamen, sondern werden gepflegt.
- **Handoffs und Ops-Artefakte** haben Zeitstempel im Dateinamen.
- **ADRs** sind nummeriert, datiert im Header, und unveränderlich nach Akzeptanz (nur „Superseded by ADR-XXXX").

## Wenn Sie unsicher sind

Beim Start mit dem Projekt:

1. Lesen Sie [PROJECT_STATE.md](PROJECT_STATE.md) — was ist gerade aktiv.
2. Lesen Sie [ROADMAP.md](ROADMAP.md) — Phasenplan.
3. Lesen Sie [ARCHITECTURE_REQUIREMENTS_DOSSIER.md](ARCHITECTURE_REQUIREMENTS_DOSSIER.md) — Was wird gebaut.
4. Lesen Sie [ENGINEERING_MANIFEST.md](ENGINEERING_MANIFEST.md) — Wie wird gebaut.
5. Lesen Sie [WORKING_AGREEMENT.md](WORKING_AGREEMENT.md) — Wie arbeiten wir zusammen.
