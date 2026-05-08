# Project State

**Stand:** 2026-05-08
**Aktive Tranche:** T0.1 — Method & Architecture Baseline
**Aktuelle Version:** 0.1.0-method-baseline (in Vorbereitung)
**Repository:** https://github.com/andreaskeis77/curio

Dieses Dokument ist die **lebende Statusübersicht** des Projekts. Es wird nach jeder relevanten Tranche aktualisiert.

---

## Was gerade gilt

- **Phase:** T0.1 läuft. Erste Tranche überhaupt.
- **Was es schon gibt:** Repo-Struktur, kanonische Dokumente, ADRs 0001–0008, ROADMAP, Konzept-Dokumente, minimale CLI-Skelett, Quality-Gate-Skript.
- **Was es noch nicht gibt:** SQLite-Registry-Schema, Capture-Pipeline, Extraction, LLM-Ingest, Web-UI, VPS-Deployment.
- **LLM-Modus:** Nur Mock-Modus geplant. Echte LLM-Calls erst ab M2.
- **Pilotbereiche im Fokus:** UNESCO und Pacojet (geplant für M1–M3). Andere Pilotbereiche bewusst zurückgestellt.

## Letzte abgeschlossene Tranche

Keine. T0.1 ist die erste Tranche.

## Aktive Tranche: T0.1

**Ziel:** Methodische und architektonische Baseline. Repo-Struktur, Dokumente, ADRs, minimale CLI, Tests grün.

**Deliverables (in Arbeit):**

- [x] Repo-Struktur
- [x] `.gitignore`, `.gitattributes`, `.env.example`, `pyproject.toml`, `README.md`
- [x] Konzeptdokumente unter `docs/concepts/`
- [x] `docs/ROADMAP.md`
- [ ] 17 kanonische `docs/`-Files (in Arbeit)
- [ ] ADRs 0001–0008
- [ ] Vault-Struktur mit READMEs
- [ ] Minimale CLI: `--help`, `--version`, `paths`
- [ ] Tests grün (pytest, ruff)
- [ ] Quality-Gate-Skript
- [ ] PowerShell-Scripts: dev, test, lint
- [ ] PR-Template
- [ ] Erster Commit und Push zu `andreaskeis77/curio`

**Blocker:** Keine.

**Nächste Tranche nach Abschluss von T0.1:** [M1 — Registry Spine](ROADMAP.md#m1--registry-spine).

## Offene rote Pfade

Keine. T0.1 hat noch keine kritischen operativen Pfade (kein Capture, kein Ingest, keine Registry).

## Bekannte Einschränkungen

- Kein echter LLM-Code in T0.1.
- Kein SQLite-Schema in T0.1 (kommt in M1).
- Kein Web-UI.
- Kein Deployment.
- Keine Capture-/Extraction-Logik.

## Aktuelle Umgebung

| Komponente | Stand |
|---|---|
| Python | 3.11+ |
| Lint | ruff 0.5+ |
| Test | pytest 8.0+ |
| Plattform | Windows 11 Pro (Dev), später Windows VPS |
| LLM Provider | Mock (T0.1) |
| Registry | nicht initialisiert (kommt in M1) |
| Web UI | nicht vorhanden (kommt in M5) |

## Zuletzt aktualisiert

- 2026-05-08 — initial.

## Wie dieses Dokument zu pflegen ist

Nach jeder abgeschlossenen Tranche:

1. „Letzte abgeschlossene Tranche" aktualisieren.
2. „Aktive Tranche" auf nächste Phase setzen.
3. „Offene rote Pfade" prüfen und ggf. schließen.
4. „Aktuelle Umgebung" aktualisieren.
5. „Zuletzt aktualisiert" mit ISO-Datum erweitern.
6. Bei Architekturwirkung: ARD und/oder ADRs aktualisieren.
7. Bei Methodikänderung: ENGINEERING_MANIFEST oder WORKING_AGREEMENT aktualisieren.
