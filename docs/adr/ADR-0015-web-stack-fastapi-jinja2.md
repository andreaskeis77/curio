# ADR-0015: Web-Stack — FastAPI plus Jinja2

- **Status:** Accepted
- **Datum:** 2026-05-09
- **Tranche:** M5 — Local Web UI

## Kontext

M5 baut die erste Web-UI fuers Curiosity Wiki. Die Architektur muss zu folgenden Randbedingungen passen:

- **Read-only im MVP** (siehe ADR-0004): kein Login, kein State-Mutating-API.
- **Lokal entwickelt, später VPS-deployed (Windows)** — Cross-Plattform-Kompatibilitaet ist Pflicht.
- **Mobile zuerst**, dann Desktop; Smartphone ist zentrales Lese-Geraet.
- **Quellen, Backlinks, Freshness, Confidence sichtbar** im Lesefluss.
- **Keine fremden Frontend-Dependencies einkaufen, die schwer wartbar sind.**
- Das Team ist **eine Person** (Andreas + Assistent). Komplexitaet zahlt sich nur aus, wenn sie wartbar bleibt.

## Optionen

### A) SPA (React/Vue/Svelte + REST/GraphQL)

- Trennung Frontend/Backend.
- Build-Pipeline (Vite/Webpack/Bundler), Node-Toolchain.
- Routing client-seitig, viele bewegliche Teile.
- Gute Mobile-Patterns durch reife Komponenten-Bibliotheken.
- Risiko: Wartung von Build-Tooling explodiert. Updates brechen Pipeline. JS-Renaissance-Halbwertszeit.

### B) Server-rendered HTML (FastAPI plus Jinja2, optional htmx)

- Templates auf dem Server, jeder Seitenwechsel ist eine HTTP-Roundtrip.
- Kein Build, kein Bundler, kein Node, kein State-Management-Framework.
- htmx fuer Mikro-Interaktionen (Source-Drawer auf-/zuklappen) per HTML-Attribut, kein JS-Code.
- Read-only-Workload passt natuerlich.

### C) Statische Generierung (z.B. mkdocs/Hugo)

- Maximal robust und performant.
- Verliert dynamische Features wie Random-Walk, Live-Search, Lint-Status.
- Suche braeuchte JS-Index (Lunr o.ae.) — bringt SPA-Komplexitaet zurueck.
- Re-Generation bei jeder Aenderung erforderlich.

## Entscheidung

**Option B: FastAPI plus Jinja2. htmx ist optional fuer einzelne Interaktionen.**

### Stack

- **FastAPI** als HTTP-Framework — async, OpenAPI-out-of-the-box, Pydantic-Modelle, klein im Footprint.
- **Jinja2** fuer Templates — ausgereift, schnell, lesbar, Whitespace-Kontrolle.
- **uvicorn** als ASGI-Server lokal; auf dem VPS spaeter ueber Reverse Proxy (siehe M6).
- **handgeschriebenes CSS** ohne CSS-Framework. Mobile-First mit `clamp()`, CSS-Custom-Properties, `@media (min-width: ...)`.
- **htmx** punktuell (Source-Drawer, Random-Walk-Refresh) — nicht als Architektur-Saeule, sondern als Mikro-Optimierung.
- **kein Node, kein Bundler, kein npm-Abhaengigkeitsbaum.**

### Verzeichnis-Layout

```text
src/curiosity_wiki/web/
  __init__.py
  app.py             # FastAPI-Instanz, Route-Registry
  api/
    __init__.py
    health.py        # /api/health
    pages.py         # /api/pages, /api/pages/{id}
    sources.py
    search.py
    browse.py
    proposals.py
    lint.py
  views/
    __init__.py
    home.py
    page.py
    search.py
    source.py
  templates/
    base.html
    home.html
    page.html
    search.html
    source.html
    partials/
      nav.html
      page_card.html
      source_drawer.html
      backlinks.html
      freshness_badge.html
  static/
    css/
      main.css
    js/
      htmx.min.js     # nur wenn benoetigt; sonst ganz weglassen
```

### Endpunkte (M5-MVP)

JSON-API:

- `GET /api/health`
- `GET /api/pages`, `GET /api/pages/{id}`
- `GET /api/sources`, `GET /api/sources/{id}`
- `GET /api/search?q=...&type=...&freshness=...&tag=...`
- `GET /api/browse/random-walk?n=5`
- `GET /api/proposals` (Liste, read-only)
- `GET /api/lint/report/latest`

HTML-Routen:

- `GET /` — Home Dashboard.
- `GET /p/<slug>` oder `/pages/<slug>` — Page Reader.
- `GET /s/<source_id>` — Source-Page mit Snapshot-Link.
- `GET /search?q=...` — Search-Page.
- `GET /healthz` — Liveness, einfach `200 OK`.

### Was ueber htmx kommt (oder gar nicht)

- **Source-Drawer auf-/zuklappen** — htmx `hx-get` einer partial, oder per CSS `<details>` ohne JS. Default: `<details>`, kein htmx.
- **Random-Walk Refresh-Button** — htmx ist hier sinnvoll, `hx-get="/api/browse/random-walk?n=5"`. Wenn unsicher, Server-Rerender pro Klick.
- **Search-Live-Suggest** — bewusst nicht in M5, kommt in Phase F.

## Begründung

- **Wartung-Surface ist klein.** Eine Person, ein Stack, ein Build (kein Build).
- **OpenAPI free.** FastAPI dokumentiert die JSON-API selbst, das ist fuer spaetere Read-only-Bots/Skripte nuetzlich.
- **Templates sind grep-bar.** Bei einem Layout-Bug muss man kein Component-Tree dekonstruieren.
- **htmx ist optional.** Einstieg ohne, Erweiterung punktuell. Falls htmx nicht gebraucht, kann es entfallen.
- **Read-only-Workload passt.** Kein State-Sync zwischen Client und Server noetig.
- **Mobile-First mit handgeschriebenem CSS** ist machbar, weil das UI-Surface klein bleibt — Hauptseiten Home/Page/Search/Source.

## Konsequenzen

### Positiv

- Kein Node, kein Bundler, kein Lockfile-Drama.
- Schneller Server-Start, leichter Debug.
- OpenAPI-Doku free.
- Server-Rendering passt natuerlich zu kontentigem Wissens-Wiki.
- Kompatibel mit Cloudflare-Tunnel-Deployment in M6.

### Negativ

- Jeder Klick ist Roundtrip — bei langsamer Verbindung sichtbar (mitigiert durch kleine Pages).
- Live-/Auto-Suggest-Suche braucht htmx oder JS in Phase F.
- Komponenten-Wiederverwendung erfolgt ueber Jinja-Includes/Macros, nicht via Component-Trees.

### Risiken und Mitigationen

| Risiko | Mitigation |
|---|---|
| HTML-Templates duplizieren Logik | Jinja-Macros plus Partials in `templates/partials/` |
| FastAPI-Sync-Funktionen blockieren | Endpunkte halten sync, da Datenbankzugriffe schnell und I/O-leicht sind; bei Bedarf einzelne Routen async machen |
| Mobile-Layout-Bugs unentdeckt | Manuelle Smoke per DevTools, plus snapshot-test auf Status-200 + Pflicht-Strings |
| Templates ohne CSP-Hardening | M6 fuegt CSP- und Security-Header hinzu |

## Bewusst nicht enthalten

- React/Vue/Svelte/Solid — nicht in Reichweite des MVP.
- Tailwind/Bulma/Bootstrap — fuer < 10 Templates Overkill.
- Service-Worker / PWA — kommt in Phase F.

## Verweise

- [ADR-0004](ADR-0004-read-only-vps-first.md) — Read-only-Architektur
- [ADR-0005](ADR-0005-web-ui-read-models.md) — Read Models statt direktem Markdown-Lesen
- [ROADMAP.md](../ROADMAP.md) — M5
