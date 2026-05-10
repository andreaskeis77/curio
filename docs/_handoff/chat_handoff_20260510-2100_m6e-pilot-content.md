# Chat Handoff — M6e Pilot-Content + Production-Bundle

**Erstellt:** 2026-05-10
**Letzte abgeschlossene Tranche:** M6e — Pilot-Content (UNESCO/Alhambra/Pacojet) + Bundle
**Naechster Schritt:** Andreas deployt das Bundle auf `vmd193069`.
**Repo:** https://github.com/andreaskeis77/curio

---

## Stand am Ende dieser Session

- 4 Pages im Wiki publiziert:
  - `wiki/topics/unesco-welterbe.md` (LLM-generiert via Mock-Pipeline, Pilot-Source `src_20260510_204224_2KG0`)
  - `wiki/sources/unesco-welterbe-stichtag-...md` (Source-Page, automatisch im M3-Publish entstanden)
  - `wiki/places/alhambra.md` (manuell, `human_reviewed=true`, Wikilink → UNESCO-Welterbe)
  - `wiki/methods/pacojet.md` (manuell, `human_reviewed=true`, eigene Pilot-Source `src_20260510_204446_Q0J4`)
- 2 Sources erfasst, 1 Proposal angenommen, 2 Hard-Facts mit Claim-Markern.
- Wikilinks: 2× Alhambra ↔ UNESCO-Welterbe sauber aufgeloest, broken-links 0.
- Quality Gates 4/4 gruen, Goldens 11/11 PASS, Lint 0 Errors (2 Warnings + 1 Info, alle erwartet).
- Bundle gebaut (siehe unten), 0 raw/-Files im ZIP, Hash-Manifest stimmt.

## Production-Bundle

| Feld | Wert |
|---|---|
| Pfad lokal | `c:\projekte\curio\dist\curiosity-bundle-23ec51a2-20260510-204954.zip` |
| Groesse | 177.062 Bytes (~173 KB) |
| Files | 122 (davon 121 in `manifest.json` mit SHA-256) |
| SHA-256 (Bundle) | `f2a43f939d1b4dd63b9e2e3520e703cbe4273657e4d431fef4a4e0c0d42cfcc6` |
| git_sha | `23ec51a2ea60eb96bb926bf9cfce4c201bc63c40` (Tag-Snapshot `v0.8.0-first-update-scout`) |
| Sanitized sources | 0 (kein privater Source-Snapshot enthalten) |

Verifizierte Pilot-Pages im Bundle:

```
wiki/methods/pacojet.md
wiki/places/alhambra.md
wiki/sources/unesco-welterbe-stichtag-die-welterbeliste-umfasst-aussergewoehnliche-kultur-u.md
wiki/topics/unesco-welterbe.md
```

## Andreas-Block — VPS-Deploy auf `vmd193069`

Der ganze Deploy ist `read-only-Bundle → Skript laeuft auf VPS → Healthz-Smoke`. Auto-Rollback ist im Skript.

### 1. (Lokal, Andreas-Laptop) Bundle-Hash zur Sicherheit nochmal pruefen

```powershell
cd c:\projekte\curio
$bundle = "dist\curiosity-bundle-23ec51a2-20260510-204954.zip"
(Get-FileHash -Path $bundle -Algorithm SHA256).Hash.ToLower()
# erwartet: f2a43f939d1b4dd63b9e2e3520e703cbe4273657e4d431fef4a4e0c0d42cfcc6
```

### 2. (Lokal) Bundle ueber Tailscale-SMB nach `c:\curiosity\incoming\` der VPS schieben

Tailnet-Hostname laut PROJECT_STATE: `vmd193069`. Falls dein bisheriger SMB-Alias `vps-curiosity` heisst (so steht's im RUNBOOK Beispiel), nimm den.

```powershell
$bundle = Get-ChildItem dist\curiosity-bundle-23ec51a2-*.zip |
          Sort-Object LastWriteTime -Descending |
          Select-Object -First 1
Copy-Item $bundle.FullName \\vmd193069\c$\curiosity\incoming\
# Falls SMB-Auth zickt: alternativ scp ueber Tailscale-SSH:
#   scp $bundle.FullName Administrator@vmd193069:/c:/curiosity/incoming/
```

### 3. (VPS via RDP/Tailscale) Deploy ausloesen

```powershell
cd c:\curiosity\app
# Bundle-Name aus Schritt 2 einsetzen:
$bundleZip = "C:\curiosity\incoming\curiosity-bundle-23ec51a2-20260510-204954.zip"
.\scripts\deploy-windows-vps.ps1 -BundleZip $bundleZip
```

Was das Skript macht (siehe `scripts/deploy-windows-vps.ps1`):

1. Preflight: Manifest gegen Bundle-Inhalt hashen.
2. Pre-Deploy-Backup nach `c:\curiosity\backups\pre-deploy\…zip`.
3. `curiosity-web` stoppen.
4. Bundle-Inhalt nach `c:\curiosity\app` kopieren.
5. `pip install -e .` im venv (idempotent).
6. `registry init`, `index rebuild`, `readmodels rebuild`.
7. `curiosity-web` starten.
8. `/healthz/deep`-Smoke (60s Timeout). Bei Fail: **Auto-Rollback** aus dem Pre-Deploy-Backup via `restore-windows-vps.ps1`.

### 4. (VPS) Lokaler Smoke gegen WinSW-Service

```powershell
Invoke-RestMethod http://127.0.0.1:8765/healthz/deep | ConvertTo-Json -Depth 5
# erwartet: status = ok (oder degraded mit Begruendung), pages_count >= 4
```

### 5. (Andreas-Laptop) Browser-Verifikation

- https://wiki.capsule-studio.de/ — Home-Dashboard mit den 4 Pages.
- https://wiki.capsule-studio.de/p/unesco-welterbe — Topic-Page, Belegte-Fakten-Block, Quellen-Drawer (UNESCO-Welterbe-Stichtag …).
- https://wiki.capsule-studio.de/p/alhambra — Place-Page, Wikilinks zu UNESCO-Welterbe (zweimal: Kurzfassung + „Warum interessant").
- https://wiki.capsule-studio.de/p/pacojet — Method-Page, Quellenliste mit Pacojet-Pilot-Source.
- Suche „UNESCO" → 2 Treffer. Suche „Pacojet" → 1 Treffer.

## Wenn der Deploy fehlschlaegt

Das Skript triggert **automatisch** Rollback aus dem Pre-Deploy-Backup, sobald
`/healthz/deep` nicht in 60 s ok/degraded liefert oder ein Schritt einen Exit
ungleich 0 wirft. Sichtbar an `[deploy] DEPLOY FAILED: …` plus
`rolling back from C:\curiosity\backups\pre-deploy\…`.

Manuelle Diagnose, wenn der Auto-Rollback selbst weh tut:

```powershell
# 1. Service-Stand
Get-Service curiosity-web, cloudflared
# 2. Letzte Log-Zeilen (WinSW)
Get-Content c:\curiosity\service\logs\curiosity-web.out.log -Tail 60
Get-Content c:\curiosity\service\logs\curiosity-web.err.log -Tail 60
# 3. Letzten Pre-Deploy-Backup explizit zurueckholen (falls Auto-Rollback nicht griff)
$lastBackup = Get-ChildItem c:\curiosity\backups\pre-deploy\curiosity-backup-pre-deploy-*.zip |
              Sort-Object LastWriteTime -Descending | Select-Object -First 1
.\scripts\restore-windows-vps.ps1 -BackupZip $lastBackup.FullName
```

Wenn Cloudflared Tunnel down ist (Browser bekommt 502/1033): `Restart-Service cloudflared`. Tunnel-Token sitzt in der System-Env `CLOUDFLARE_TUNNEL_TOKEN`.

## Was bewusst nicht in M6e ist

- **Kein neuer Tag.** Andreas tagged erst, wenn die VPS das Bundle wirklich serviert. Dann z.B. `v0.9.0-pilot-content` oder so — siehe `RELEASE_PROCESS.md`.
- **Kein Auto-Push der Pages auf die VPS.** Bundle bleibt Bundle, Andreas zieht den Trigger.
- **Keine zusaetzlichen Manual-Pages.** 3 sind genug fuer den Pilot-Beweis.

## Lessons aus dieser Session

- **Manuelle Pages ohne `pages`-Tabelle** sind ein bekanntes Roadmap-Loch. Phase A „Registry-Rebuild aus Markdown" wird das aufloesen. Fuer M6e habe ich einen einmaligen Helper `_tmp_register_manual_pages.py` im Repo-Root benutzt (Pages aus Markdown in `pages`/`page_sources`/`links`/`pages_fts` einfuegen), nach dem Lauf wieder geloescht. Phase A macht daraus die richtige `curiosity registry import-md`-CLI.
- **Wikilink-Aufloesung beim Publish** schreibt Links auch dann ein, wenn das Ziel noch nicht existiert (Status `broken`). Phase A bringt einen globalen Re-Resolve-Pass — fuer M6e habe ich einmalig ein 5-Zeiler-Snippet gegen die DB gefahren, um die UNESCO→Alhambra-Links auf `resolved` zu setzen. Der Effekt ist im Bundle nicht mehr sichtbar (Bundle haelt nur Markdown + Read-Models), aber lokal in der Dev-Registry persistent. **Auf der VPS** laeuft das Deploy-Skript ohnehin frische `registry init` + `index rebuild` + `readmodels rebuild`; broken-link-Status wird beim naechsten Phase-A-Schritt sauber regeneriert.
- **Source-Page-Wikilinks** mit Auto-Slug-Truncation (z.B. `[[UNESCO-Welterbe-Stichtag: Die Welterbeliste umfasst aussergewoehnliche Kultur- u]]`) sind haesslich — ich habe sie in den manuellen Pages durch Klartext ersetzt. Die DB-`page_sources`-Linkage bleibt korrekt; der Source-Drawer im Web-UI nutzt sie.
- **`.gitignore`-Bug entdeckt und gefixt:** Die Patterns waren auf `raw/notes/*` und `raw/screenshots/*` (Plural) gesetzt, die echten `SourceType.value`-Pfade sind aber Singular (`raw/note/`, `raw/screenshot/`). Heisst: Wer eine Note via `curiosity capture note` gespeichert haette und blind `git add .` gemacht haette, haette private Raw-Inhalte ins Repo geschoben. Pattern auf Singular korrigiert + `raw/file/*` erganzt (`SourceType.FILE` war komplett unbedacht).

## Cold-Recovery fuer naechste Session

```powershell
cd c:\projekte\curio
.\.venv\Scripts\Activate.ps1
python -m curiosity_wiki info        # Schema 5, Pages 4
python -m curiosity_wiki pages list  # Alhambra, Pacojet, UNESCO-Welterbe (topic + source)
python -m pytest -q                  # erwartet: 286 passed
git log --oneline -3
ls dist\curiosity-bundle-*.zip
```

Falls die VPS noch nicht ueber dem neuen Bundle laeuft: das Andreas-Block oben Schritt fuer Schritt ausfuehren.
