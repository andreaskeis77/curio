# Release Process

**Status:** v0.1
**Stand:** 2026-05-08

---

## Release-Level

| Level | Bedeutung | Beispiel |
|---|---|---|
| **Methodik Release** | Regeln/Doku/Agreement | `v0.1.0-method-baseline` |
| **Architektur Release** | Layer/Registry/Agent-Entscheidung | `v0.2.0-registry-spine` |
| **Runtime Release** | CLI, Registry, Ingest, UI | `v0.3.0-proposal-ingest` |
| **Content Release** | kuratierte Wiki-Inhalte | `v0.4.0-unesco-pacojet-mvp` |
| **Ops Release** | Deployment/Backup/Runbook | `v0.6.0-vps-readonly-preview` |

## Versionierung

Pragmatisch, nicht strikt SemVer:

```text
v0.1.0-method-baseline       # T0.1
v0.2.0-registry-spine        # M1
v0.3.0-proposal-ingest       # M2
v0.4.0-wiki-review-publish   # M3
v0.5.0-local-web-mvp         # M5 (M4 ist intern)
v0.6.0-vps-readonly-preview  # M6
v1.0.0-curiosity-mvp         # M7 abgeschlossen
```

Nach v1.0: SemVer wird strikter (MAJOR.MINOR.PATCH).

## Release-Schritte

### 1. Pre-Flight

- [ ] Aktive Tranche ist abgeschlossen (Definition of Done in [ENGINEERING_MANIFEST.md](ENGINEERING_MANIFEST.md)).
- [ ] PROJECT_STATE.md ist aktuell.
- [ ] Validierungsleiter mindestens bis Stufe 6 grün ([VALIDATION_PROTOCOL.md](VALIDATION_PROTOCOL.md)).
- [ ] Keine offenen kritischen Issues.

### 2. Quality Gate Run

```powershell
python tools/run_quality_gates.py
```

Output landet in `docs/_ops/quality_gates/<timestamp>/`.

### 3. Release Notes

Datei: `docs/_ops/releases/v<version>.md`.

Inhalt:

```markdown
# v<version> — <Titel>

**Datum:** YYYY-MM-DD
**Tranche:** T<x.y>

## Zweck

<warum dieses Release>

## Scope

- <was ist enthalten>

## Bewusst nicht enthalten

- <was wurde verschoben>

## Validierung

- Stufen ausgeführt: ...
- Coverage: ...
- Bekannte Einschränkungen: ...

## Bewusste Trade-offs

- ...

## Rollback

Bei Problemen: `git checkout v<previous>` und Backup einspielen.

## Nächste Tranche

T<x.y+1> — siehe [ROADMAP](../../ROADMAP.md).
```

### 4. Tag

```powershell
git tag -a v0.1.0-method-baseline -m "Method & Architecture Baseline"
git push origin v0.1.0-method-baseline
```

### 5. PROJECT_STATE und Handoff aktualisieren

- PROJECT_STATE.md: „Letzte abgeschlossene Tranche" auf neue Version.
- `docs/_handoff/chat_handoff_<timestamp>_release-v<version>.md` erstellen.

### 6. Optional: GitHub Release

```powershell
gh release create v0.1.0-method-baseline --title "Method & Architecture Baseline" --notes-file docs/_ops/releases/v0.1.0-method-baseline.md
```

## Release Evidence

Pro Release wird abgelegt:

```text
docs/_ops/releases/
  v0.1.0-method-baseline.md
docs/_ops/quality_gates/
  20260508-203000_v0.1.0/
    pytest.log
    ruff.log
    secret_scan.log
    summary.md
```

## Wann ist ein Release nötig?

| Trigger | Release? |
|---|---|
| Tippfehler in Doku | nein |
| Neue ADR | nein (außer architekturkritisch) |
| Ende einer Tranche T<x.y> | ja (Tag) |
| Phase-Abschluss (M1, M2, ...) | ja (Tag + Notes) |
| Hotfix | ja (Patch-Tag) |
| Vor VPS-Deploy | ja (Pflicht) |

## Vor VPS-Deploy (ab M6)

Zusätzlich zum Standard-Release:

- [ ] Publish-Bundle erzeugt und geprüft (keine privaten Raw Sources).
- [ ] Backup-Skript läuft.
- [ ] Restore-Drill ausgeführt.
- [ ] Healthcheck-Endpunkt verifiziert.
- [ ] Rollback-Plan dokumentiert.
- [ ] Deployment-Evidence in `docs/_ops/deployment_evidence/`.

## Verweise

- [ENGINEERING_MANIFEST.md](ENGINEERING_MANIFEST.md) — Definition of Done
- [VALIDATION_PROTOCOL.md](VALIDATION_PROTOCOL.md) — Validierungsleiter
- [DELIVERY_PROTOCOL.md](DELIVERY_PROTOCOL.md) — Tranchen
- [ROADMAP.md](ROADMAP.md) — Phasenplan
