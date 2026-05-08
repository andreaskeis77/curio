# Methodik und Lessons Learned aus `capsule` und `new_nfl`

**Status:** Historische Referenz (Stand 2026-05-07)
**Kanonische Engineering-Regeln:** [../ENGINEERING_MANIFEST.md](../ENGINEERING_MANIFEST.md)
**Working Agreement:** [../WORKING_AGREEMENT.md](../WORKING_AGREEMENT.md)

Dieses Dokument fasst die methodischen Lessons aus den Vorprojekten `capsule` und `new_nfl` zusammen, die in das Curiosity Wiki einfließen.

---

## Kernerkenntnis

> Das Curiosity Wiki darf nicht als loses KI-Experiment starten. Es muss vom ersten Tag an als langlebiges, versioniertes, überprüfbares Knowledge-System gebaut werden.

## Was aus `capsule` übernommen wird

| Lesson | Übertragung |
|---|---|
| **Projekt ist Produkt, nicht Demo** | Engineering-Rahmen ab Tag 0: PROJECT_STATE, RUNBOOK, Release-Definition |
| **Kanonische Dokumente verhindern Chat-Wissensverlust** | 17 docs/-Files, ADRs, _handoff/, _ops/ |
| **ARD als lebender Architekturanker** | docs/ARCHITECTURE_REQUIREMENTS_DOSSIER.md |
| **Engineering Manifest als Arbeitsvertrag** | docs/ENGINEERING_MANIFEST.md mit 15 Grundprinzipien |
| **Runbooks machen Betrieb reproduzierbar** | DEV-LAPTOP, lokale CLI, Web-UI, Backup, Restore, VPS |
| **Security- und Secret-Hygiene früh** | docs/SECURITY.md, docs/SOURCE_POLICY.md, .env in .gitignore |
| **Quality Gates als Einstiegspunkt** | tools/run_quality_gates.py mit klarer Reihenfolge |
| **Handoff-Fähigkeit ist Qualität** | docs/_handoff/ pro Tranche |
| **Architektur und Betrieb sind nicht getrennt** | VPS-Modell früh skizzieren, aber read-only zuerst |
| **Dokumentationsbreite kontrollieren** | docs/INDEX.md mit klarer Hierarchie |

## Was aus `new_nfl` übernommen wird

| Lesson | Übertragung |
|---|---|
| **Datenintegrität schlägt Geschwindigkeit** | Quellenintegrität, Reproduzierbarkeit, Robustheit vor Tempo |
| **Layer-Modell: Raw / Staging / Core / Mart / Meta** | raw/ → extracted/ → wiki/+registry → read_models/ → meta |
| **Immutable Raw-Landing und Replay sind Pflicht** | SHA-256, Run Evidence, Prompt-Versionen |
| **Metadata-driven Operation statt Datei-Pfaden** | SQLite Registry mit Sources, Runs, Claims, Proposals etc. |
| **Quarantäne ist First-Class** | quarantine_cases mit Severity, Evidence, Recommended Action |
| **Designed Degradation für Update Scouts** | Wenn Quelle ausfällt: Status `unknown`/`stale`, kein Schaden |
| **Read-Model-Trennung schützt UI** | UI liest aus read_models/, schreibt nicht in wiki/ |
| **UI-Qualität ist Systemqualität** | docs/UI_UX_GUIDE.md, mobile-first, Source Badges |
| **Validierung ist eine Leiter** | 10-stufiges Validation Protocol |
| **Fresh State und Evolved State sind beide wichtig** | Tests in beiden Modi |
| **Retrospektiven sind Methodik-Input** | docs/LESSONS_LEARNED.md, docs/_handoff/ |
| **Delivery-Protokoll reduziert Friction** | docs/DELIVERY_PROTOCOL.md |

## Curiosity-Layer-Modell (aus NEW-NFL adaptiert)

| NEW-NFL | Curiosity | Zweck |
|---|---|---|
| `raw/` | `raw/` | Unveränderte Quellen-Snapshots, Hashes, Receipts |
| `stg.*` | `extracted/` + `registry.extractions` | Extrahierter Text, Metadaten, Parsed Content |
| `core.*` | `wiki/` + `registry.pages/claims` | Kuratierte Synthese, Claims, Seiten, Links |
| `mart.*` | `read_models/` | Web-optimierte, rebuildbare Darstellungen |
| `meta.*` | `data/registry/curiosity.sqlite` | Sources, Runs, Jobs, Proposals, Reviews, Freshness, Lint |
| Quarantine | `quarantine/` + `registry.quarantine_cases` | Fehlerhafte Quellen, unsichere Claims |
| Replay | `tools/replay_ingest.py` (später) | Quelle erneut mit definierter Prompt-/Tool-Version verarbeiten |

## Curiosity-Validierungsleiter (10 Stufen)

1. Repo-/Pfad-Sanity
2. Import-/CLI-Gate
3. Schema-/Registry-Gate
4. Letzter grüner Pfad
5. Neuer Pfad
6. Wiki-Integrity-Gate (Links, Frontmatter, Quellen, Claims, Duplicates, Freshness)
7. LLM-Fidelity-Gate (Fixture → erwartete Proposal-Struktur)
8. UI-Smoke
9. Ops-/Backup-Gate
10. Release Evidence

Vollständig in [../VALIDATION_PROTOCOL.md](../VALIDATION_PROTOCOL.md).

## Anti-Patterns die wir vermeiden

1. LLM schreibt direkt ins produktive Wiki.
2. Markdown-only ohne Registry.
3. Quellen werden überschrieben statt versioniert.
4. Zu viele Pilotdomänen im MVP.
5. Web-UI erst spät und dann hektisch.
6. VPS bekommt Schreibrechte, bevor Review/Backup/Rollback stabil sind.
7. Prompts ändern sich ohne Version und Tests.
8. Doku bleibt im Chat.
9. Quality Gates werden optional.
10. Rote operative Pfade werden schöngeredet.
11. Private Raw Sources landen versehentlich im Publish-Bundle.
12. Source Policy wird erst nach problematischem Ingest geklärt.
13. UI liest direkt aus Raw/Registry statt aus Read Models.
14. Agenten bekommen zu breite Aufgaben ohne Tranche-Scope.
15. Keine Fresh-/Evolved-State-Tests.

## Methodenleitsatz

> Alles darf gesammelt werden, aber nichts wird ungeprüft zur Wahrheit. Jede Quelle bleibt nachvollziehbar, jede Synthese bleibt überprüfbar, jede Agentenänderung bleibt reviewbar, und jeder produktive Stand bleibt reproduzierbar.

## Operativ verkürzt

```text
Capture fast.
Preserve raw.
Extract carefully.
Propose with evidence.
Review before publish.
Lint continuously.
Deploy read-only first.
Document every architectural decision.
```
