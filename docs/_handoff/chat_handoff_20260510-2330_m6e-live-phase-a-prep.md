# Chat Handoff — M6e Live + Phase-A-Vorbereitung

**Erstellt:** 2026-05-10 (Spätabend nach erfolgreichem Live-Deploy)
**Letzte abgeschlossene Tranche:** M6e Pilot-Content live auf wiki.capsule-studio.de (Tag `v0.9.0-pilot-content`)
**Naechste Tranche:** Phase A1 — `curiosity registry import-md` (Empfehlung), oder freie Wahl aus Phase A
**Repo:** https://github.com/andreaskeis77/curio

---

## Stand am Ende dieser Session

- 4 Pages live unter https://wiki.capsule-studio.de/ (UNESCO-Welterbe, Alhambra, Pacojet, Source-Page).
- Bundle `dist/curiosity-bundle-23ec51a2-20260510-204954.zip` (SHA `f2a43f93…d42cfcc6`) deployed via HTTPS-Pull.
- Pre-Deploy-Backup auf der VPS: `c:\curiosity\backups\pre-deploy\curiosity-backup-pre-deploy-20260510-232345.zip`.
- 286 Tests grün, Quality Gates 4/4, Goldens 11/11, Lint 0 Errors.
- Tag `v0.9.0-pilot-content` auf GitHub.
- Doku-Update durch: PROJECT_STATE, ROADMAP (Phase A in 8 Tranchen geschnitten), RUNBOOK (Deploy-Pfade umgestellt auf HTTPS-Pull-Default), LESSONS_LEARNED (3 neue Einträge).

## Was diese Session gelehrt hat — kompakt

### Deploy-Transport-Marathon (5 Anläufe für 173 KB)

1. SMB ohne Creds → Auth-Fail.
2. SMB mit `Administrator` → Netzwerkname-Fehler (falscher User).
3. SMB mit `srv-ops-admin` → Netzwerkname-Fehler. **Root cause:** `srv-ops-admin` ist nicht in der lokalen `Administrators`-Gruppe — `c$`-Adminshare verlangt das.
4. RDP-Drive-Redirection → `\\tsclient\C` leer. **Root cause:** `mstsc /v:<host>` springt direkt zum Login-Dialog und zeigt den „Lokale Ressourcen → Mehr → Laufwerke"-Dialog gar nicht erst. Plus: kann zusätzlich durch RD-Group-Policy blockiert sein.
5. `tailscale file cp` → unbekannter Subbefehl. **Root cause:** Tailscale 1.96 hat die `file`-Subkommandos entfernt, Taildrop läuft jetzt nur noch via GUI/Menü.
6. **Funktionierte:** `python -m http.server 8800` auf Laptop, `Invoke-WebRequest` von der VPS via Tailscale-IP `100.67.145.119`. Hash-Match `f2a43f93…d42cfcc6`.

→ RUNBOOK §"Pro Deploy" ist umgeschrieben: HTTPS-Pull als Default, SMB/RDP nur als Convenience für später eingerichtete Setups. Phase A2 baut daraus ein `scripts/push-bundle-to-vps.ps1`, das die Pfade automatisch durchprobiert.

### `.gitignore` Singular-vs-Plural-Bug

Die `.gitignore`-Patterns waren `raw/notes/*` und `raw/screenshots/*` (Plural), die echten `SourceType.value`-Pfade sind `raw/note/`, `raw/screenshot/` (Singular). Plus: `raw/file/*` war komplett vergessen. Heißt: Wer eine Notiz captured hätte und blind `git add .` gemacht hätte, hätte private Inhalte ins Public-Repo gepusht.

→ In M6e-Commit `e40f5b8` gefixt; Phase A3 baut einen Test, der für jeden `SourceType.value` strukturell prüft, ob `git check-ignore` greift.

### Manuelle Pages haben keinen sauberen Pfad in die Registry

`curiosity index rebuild` schreibt nur `pages_fts`, nicht `pages`/`page_sources`/`links`. Manuelle Markdown-Pages bleiben dadurch im Web-UI unsichtbar (`/p/<slug>` queryt `pages`). Workaround in M6e: einmalig ein `_tmp_register_manual_pages.py`-Helper im Repo-Root, danach gelöscht.

→ Phase A1 baut die richtige `curiosity registry import-md`-CLI. Aus dem temporären Helper wird der Skelett-Algorithmus.

## Aktive Phase-A-Roadmap (jetzt ausformuliert)

Reihenfolge (siehe ROADMAP.md §"Phase A"):

1. **A1 — `curiosity registry import-md`** ← _empfohlener Start, kleinster sicherer Schritt._
2. **A2 — `scripts/push-bundle-to-vps.ps1`**
3. **A3 — Source-Policy-Test als Quality Gate**
4. **A4 — Mehr Lint-Regeln (Ziel: 25+)**
5. **A5 — Backup/Restore als CI-Job**
6. **A6 — Bessere Proposal-Diffs**
7. **A7 — Claim-Markierung verbessern**
8. **A8 — Windows-Kompatibilität härten**

A1 und A2 sind die direkten Lessons-Pay-offs, ich würde mit einem von beiden starten — A1 ist zuerst, weil es Architektur berührt (Registry-Schreiber-Pfad), A2 ist reines Tooling.

## Empfehlung für die nächste Session

**Konzept-Phase**, Dauer ~30 Min:

- ADR-Skizze für A1 schreiben: Wie verhält sich `import-md` bei Slug-Kollision mit M3-publish? Mehrere Strategien diskutieren (skip / overwrite-with-warn / require `--force`). Letzte Wahl im ADR festhalten.
- Test-Skizze: Welcher fresh-state und welcher evolved-state? Mindestens: leeres Wiki + manuell geschriebene Page → import-md schreibt sie ein. Plus: vorhandene Page wird re-importiert → idempotent. Plus: broken-link wird beim Re-Resolve aufgelöst, sobald Ziel da ist.
- Erst dann **Implementierungs-Phase**.

Wenn lieber A2 zuerst: das ist eine 1–2-stündige PowerShell-Aufgabe ohne Architektur-Risiko, gutes „kleines Win" zwischendrin.

## Quick-Recovery für Cold-Start

```powershell
cd c:\projekte\curio
.\.venv\Scripts\Activate.ps1
python -m curiosity_wiki info        # Schema 5
python -m curiosity_wiki pages list  # 4 Pages: UNESCO topic + source, Alhambra, Pacojet
python -m pytest -q                  # 286 passed
git log --oneline -5
git tag | tail -3                    # zuoberst: v0.9.0-pilot-content
```

Web live (read-only verifizieren):

- https://wiki.capsule-studio.de/
- https://wiki.capsule-studio.de/p/unesco-welterbe
- https://wiki.capsule-studio.de/p/alhambra
- https://wiki.capsule-studio.de/p/pacojet

Falls etwas davon kippt: Pre-Deploy-Backup auf der VPS unter `c:\curiosity\backups\pre-deploy\curiosity-backup-pre-deploy-20260510-232345.zip`, Restore via `scripts/restore-windows-vps.ps1`.

## Offene Notizen, die in diese Session nicht reingepasst haben

- Lint-Heuristik produziert in der UNESCO-Page false positives für „1972"/„1978" in Prosa, obwohl die echten Claims im Belegte-Fakten-Block sauber markiert sind. → A4 (Lint-Regeln verfeinern).
- `freshness_dashboard.scouts` wird nicht automatisch nach einem Scout-Lauf neu gebaut. Kein Showstopper für M6e (Scout läuft lokal, nicht auf VPS), aber wenn Phase B (mehr Scouts) startet, braucht das einen Auto-Trigger.
- Source-Page-Slug bei Note-Capture wird aus dem Notiz-Anfang generiert und ist hässlich (`unesco-welterbe-stichtag-die-welterbeliste-umfasst-aussergewoehnliche-kultur-u`). Cosmetic; eigene Mini-Tranche wert, sobald A1 die Re-Insert-Logik bringt.

## Methodik-Hinweis

Working Agreement war heute Implementierungs-Phase, output-basiert, ein Schritt pro kritischem Zustand — und das hat gehalten, sogar als der Bundle-Push eine Stunde Diagnose brauchte. Kein Pfusch, kein Pre-Mature-Push. Tag erst nach Browser-Verifikation.

Gute Nacht.
