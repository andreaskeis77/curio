# Chat Handoff — M5 Ende / M6 Start (VPS Read-only Preview)

**Erstellt:** 2026-05-09
**Letzte abgeschlossene Tranche:** M5 — Local Web UI (`v0.6.0-local-web-ui`, Tag in Vorbereitung)
**Nächste Tranche:** M6 — VPS Read-only Preview
**Repo:** https://github.com/andreaskeis77/curio

---

## Zustand am Ende dieser Session

- 249 pytest-Tests grün, alle 4 Quality Gates grün (pytest, ruff check, ruff format, secret-scan).
- Working Tree sauber bis auf den letzten M5d-Commit.
- ADRs 0001–0016. ADR-0015 dokumentiert Web-Stack (FastAPI + Jinja2), ADR-0016 die Read-Model-Builder-Strategie.
- CLI: alle bisherigen + `readmodels rebuild|status` und `web run`.
- Web-Stack ist lokal lauffähig: `curiosity web run` startet uvicorn auf 127.0.0.1:8765.
- Read-Models in `read_models/`: `site_index.json`, `graph.json`, `search_documents.jsonl`, `freshness_dashboard.json`, `page_cards.json`, `mobile_nav.json`, `open_questions.json`. `read_models/` ist gitignored (generated).

## Was nicht im PROJECT_STATE steht (Notizen für die nächste Session)

### 1. Mobile-Smoke ist offen

`tests/test_views.py` deckt HTML-Status, Skip-Link, role-Landmarks, Wikilink-Resolution. Ein echter Browser-Smoke (DevTools, Mobile-Viewport ≥ 320px) ist **nicht** automatisiert. Andreas muss vor M6-Deployment lokal `curiosity web run` öffnen und mindestens Home, Page-Reader, Search, Source auf 320–375px Breite prüfen.

### 2. Read-Models werden nicht beim Publish gebaut

ADR-0016 hat sich gegen Auto-Hook beim Publish entschieden. Workflow: nach Approves einmal `curiosity readmodels rebuild`, dann `curiosity web run` neu starten (ggf. mit `--reload`). Wenn das in der Praxis stört, einen `CURIOSITY_READMODELS_AUTO_REBUILD=true`-Hook in `wiki/publish.py` ergänzen — der Code-Punkt ist dort, wo `index_page` aufgerufen wird.

### 3. Wikilink-Resolution lebt im View, nicht im API

`web/templating.py::resolve_wikilinks` ersetzt `[[Title]]` für die HTML-Render. Die JSON-API liefert weiterhin den rohen `body_markdown` — Konsumenten der API müssten selbst auflösen, falls sie wollen. Für M6/Phase E: ggf. die Logik ins `read_models/`-Layer ziehen, damit sie für UI und API gleich ist.

### 4. SQLite-Connections per Request

`web/dependencies.py::get_conn` öffnet pro Request eine eigene Connection. Das ist OK für lokales Read-only-Workload, kann aber bei VPS unter Last zum Bottleneck werden. M6 sollte bei Bedarf einen Connection-Pool erwägen — `sqlite3` selbst hat keinen, aber eine kleine Wrapper-Klasse mit `threading.local` wäre einfach.

### 5. Static-Files sind im Package, nicht im Vault

CSS/Templates liegen unter `src/curiosity_wiki/web/static/` und `web/templates/`. Sie werden vom installierten Paket geliefert, **nicht** aus dem Vault gelesen. Für M6: das Deployment muss das Paket installiert haben, nicht nur den Vault.

### 6. FastAPI-Pattern + Ruff B008

`pyproject.toml` hat per-file-ignore `B008` für `src/curiosity_wiki/web/**`, weil `Depends(...)` und `Query(...)` als Default-Werte FastAPI-Standard sind. Wenn neue Web-Module entstehen, daran denken (oder neue Pfade unter `web/` lassen).

### 7. CLI-Help-String pflegen

Top-Level-Help und `info`-Footer wurden auf "M5 Local Web UI" aktualisiert. M6 entsprechend ändern.

### 8. uvicorn-Reload zum Entwickeln

`curiosity web run --reload` nutzt uvicorn-Hot-Reload. Funktioniert auf Windows, kann aber bei großen Wiki-Bäumen langsam starten (rglob über `wiki/`). Im Dev-Modus ggf. Sub-Vault nutzen.

## M6 Scope (aus ROADMAP.md)

**Ziel:** Kontrolliertes read-only Deployment auf Windows-VPS.

### Deliverables

- Publish-Bundle-Builder: Filtert private Raw Sources, packt nur freigegebene Wiki-Seiten + Read Models + nicht-private Source-Metadaten.
- Deployment-Skript `scripts/deploy-windows-vps.ps1`: Preflight, Backup, Deploy, Migration, Index-Rebuild, Service-Restart, Healthcheck, Rollback.
- Windows-Service-Konfiguration via WinSW oder NSSM.
- Reverse Proxy: Caddy oder Cloudflare Tunnel.
- Tailscale für Admin-Zugang.
- Windows-Firewall-Baseline.
- Backup-Skript: Repo-Bundle, Raw-Blobs (lokal!), SQLite-Registry, Manifest, Hash.
- Backup-Task via Windows Scheduled Task.
- Restore-Skript und Restore-Drill.
- Health-Endpoint: `/healthz` (vorhanden), `/healthz/deep` (neu).
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

### Bewusst nicht in M6

- Schreibfunktionen auf VPS.
- Login/Auth für Admin-Funktionen (Phase D4).
- Multiuser.

## Tipps für die Umsetzung

1. **Publish-Bundle-Builder** als CLI: `curiosity bundle build`, schreibt nach `dist/curiosity-bundle-<sha>.zip`. Whitelist im Code: `wiki/`, `read_models/`, `data/registry/curiosity.sqlite` (bereinigt um private Sources), Public-Source-Manifests. Private Raw-Blobs (`raw/`) und `.env` explizit ausschließen.

2. **Deployment-Skript** macht: Preflight (existiert WinSW-Service?), Backup ZIP, ZIP entpacken, `pip install -e .`, `python -m curiosity_wiki registry init`, `python -m curiosity_wiki index rebuild`, `python -m curiosity_wiki readmodels rebuild`, Service-Restart, `curl /healthz/deep`, bei Fail Rollback.

3. **`/healthz/deep`** prüft: Registry erreichbar, Schema-Version stimmt, mindestens ein Read-Model existiert, FTS5-Tabelle vorhanden, kein Lint-Error in `latest`. JSON-Response mit `status: ok|degraded|down`.

4. **Tailscale + Cloudflare Tunnel**: Tailscale für RDP-Admin (private Wartung), Cloudflare Tunnel für Public-Web. Firewall-Regel: nur Tailscale-IPs für RDP, sonst nichts inbound.

5. **Tests M6**: Bundle-Builder-Test (whitelist-Logik), Restore-Drill als pytest, Smoke-Test gegen lokal gestarteten Service via httpx.

## Nicht-vergessen-Liste

- [ ] ADR-0009 README-Eintrag für ADR-0017/0018 ergänzen.
- [ ] PROJECT_STATE.md auf M6-Scope aktualisieren wenn fertig.
- [ ] Quality Gates komplett grün.
- [ ] Bundle-Builder testen (kein privater Inhalt drin).
- [ ] Restore-Drill mindestens einmal grün.
- [ ] Tag `v0.7.0-vps-read-only-preview`.
- [ ] Diesen Handoff bei Bedarf als „abgeschlossen" markieren.

## Quick-Recovery für Cold Start

```powershell
cd c:\projekte\curio
.\.venv\Scripts\Activate.ps1
python -m curiosity_wiki info        # zeigt Phase, Schema-Version, Source-Count
python -m pytest -q                  # erwartet: 249 passed
python tools\run_quality_gates.py    # erwartet: 4/4 OK
git log --oneline -7                 # erwartet: M5d-Commit zuoberst
git tag                              # erwartet: v0.6.0-local-web-ui
python -m curiosity_wiki readmodels rebuild
python -m curiosity_wiki web run     # http://127.0.0.1:8765
```

Falls etwas anders: PROJECT_STATE.md prüfen, dort steht der wahre Stand.
