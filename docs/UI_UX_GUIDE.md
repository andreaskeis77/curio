# UI/UX Guide

**Status:** v0.1 — Designprinzipien für M5 (Local Web UI) und M6 (VPS Read-only)
**Stand:** 2026-05-08

---

## Produktprinzipien für das Interface

1. **Lesen vor Verwalten.** Die Oberfläche muss zuerst ein schöner Lese- und Entdeckungsraum sein.
2. **Provenienz sichtbar, aber nicht störend.** Quellen, Confidence und Freshness sind sichtbar, ohne den Lesefluss zu zerstören.
3. **Mobile-first Navigation.** Smartphone-Nutzung ist kein Nachgedanke.
4. **Schneller Einstieg.** Startseite zeigt sofort interessante Wiedereinstiege.
5. **Review als natürlicher Workflow.** Vorschläge müssen leicht prüfbar sein (ab Phase D4).
6. **Keine Graph-Spielerei als Kern.** Graphen optional. Gute Listen, Pfade, Backlinks und Sammlungen sind wichtiger.

## Hauptbereiche (Site-Map)

```text
Home
Search / Ask
Browse
Pages (Topics, Places, People, Recipes, Methods, Products, ...)
Collections
Sources
Review Queue           (lokal/admin only)
Open Questions
Freshness
Settings
```

## Home Dashboard

Die Startseite ist **kein leeres Suchfeld**. Module:

- **Weiterlesen:** zuletzt gelesene/aktualisierte Seiten.
- **Heute interessant:** 3–5 vorgeschlagene Seiten.
- **Offene Fragen:** kleine Karten mit Themenbezug.
- **Needs Review:** neue Ingest-Vorschläge (lokal).
- **Veraltet / Review fällig:** Produkt- und Eventseiten mit `review_after` überschritten.
- **Unverarbeitete Quellen:** Raw Inbox (lokal).
- **Random Walk:** zufälliger Lesepfad.

## Layout

### Desktop (> 1024px)

3-Spalten:

```text
┌──────────────┬──────────────────────────┬──────────────────┐
│ Navigation   │ Lesebereich              │ Kontext          │
│ Themen       │ Titel                    │ Quellen          │
│ Sammlungen   │ Kurzfassung              │ Freshness        │
│ Suche        │ Inhalt                   │ Backlinks        │
│ Inbox        │ Wikilinks                │ Offene Fragen    │
└──────────────┴──────────────────────────┴──────────────────┘
```

### Tablet (768–1024px)

2-Spalten: Navigation einklappbar, Kontextspalte als Drawer.

### Mobile (< 768px)

```text
┌────────────────────────┐
│ Top Bar: Suche + Menü  │
├────────────────────────┤
│ Titel + Badges         │
├────────────────────────┤
│ Kurzfassung            │
│ Inhalt                 │
│ Wikilinks im Text      │
├────────────────────────┤
│ Quellen / Backlinks    │  als einklappbare Drawer
├────────────────────────┤
│ Bottom Navigation      │
└────────────────────────┘
```

**Wichtig für Mobile:**

- Keine seitlichen Pflichtspalten.
- Große Touch-Ziele (>= 44px).
- Gute Typografie mit Lesegröße.
- Inhaltsverzeichnis einklappbar.
- Quellen als Drawer.
- „Weiterlesen"-Links am Ende.

## Wiki-Seiten-Komponenten

Jede Wiki-Seite hat:

- **Titel** — h1.
- **Typ-Badge** — Topic, Person, Place, Product Research, Recipe, Method, Experiment, Collection.
- **Freshness-Badge** — stable, periodic, volatile, personal.
- **Confidence-Badge** — low, medium, high.
- **Last checked** — bei volatilen Seiten.
- **Kurzfassung** — 1–3 Sätze nach Titel.
- **Hauptinhalt** — Markdown gerendert.
- **Quellenpanel** — rechte Spalte (Desktop) oder Drawer (Mobile).
- **Backlinks** — welche Seiten verlinken hierhin?
- **Verwandte Seiten** — gleiche Tags, gleiche Sammlung.
- **Offene Fragen** — falls vorhanden.
- **Änderungsverlauf** — letzte Verarbeitung.

## Status-Badges (konsistente Semantik)

| Badge | Farbe (Konvention) | Bedeutung |
|---|---|---|
| Stable | grün | Stabiles Wissen, selten zu aktualisieren |
| Periodic | gelb | Regelmäßige Reviews nötig |
| Volatile | orange | Schnell veraltet (Produkte, Events) |
| Personal | blau | Eigene Notizen / Experimente |
| Verified | grün | Quellen geprüft |
| Needs Review | gelb | Wartet auf manuelle Prüfung |
| Stale | rot | `review_after` überschritten |
| Unsicher | grau | Unklare Confidence |

## Source-Anzeige

Pro Quelle in der Quellenliste:

- Quellen-Titel (klickbar zur Source Page).
- Reliability-Badge.
- Erfasst am: Datum.
- Snapshot-Hash (Tooltip).
- Externer Link (mit `rel="noopener noreferrer"`).

## Claim-Anzeige (ab M3)

Bei Fakten-Aussagen mit Claim-Marker:

```markdown
Die Stätte wurde 1984 in die Welterbeliste aufgenommen.
[Quelle: src_20260505_unesco_alhambra]
```

Im Hover oder als Tooltip:

- Claim-ID
- Source-ID
- Verified-Datum
- Confidence

## Browse-Funktionen

Nicht nur Suche, sondern Schmökerbarkeit:

- „Zeig mir 5 Seiten aus alten Interessen."
- „Lesepfad zu Haute Couture."
- „Ungewöhnliche Verbindung: Motorsport ↔ Markenmythos."
- „Offene Fragen zu Pacojet."
- „Quellen, die noch keine Wiki-Seite erzeugt haben."
- „Seiten mit niedriger Confidence."
- „Produktrecherchen, die fällig sind."

## Designsystem (MVP)

- 1 Schrift für UI (System-Font-Stack).
- 1 gute Leseschrift (z.B. Charter, Source Serif, oder System).
- Definierte Spacing-Skala (4px Basis: 4, 8, 16, 24, 32, 48, 64).
- Karten für Quellen, Fragen, Seiten und Proposals.
- Konsistente Status-Badges (siehe oben).
- Dark Mode optional, aber Architektur dafür vorbereiten.
- Responsive Breakpoints: 768px, 1024px.

## Accessibility (Pflicht ab M5)

- Semantische HTML-Struktur (`<main>`, `<nav>`, `<article>`, `<aside>`).
- Tastaturnavigation (Tab-Order korrekt).
- Sichtbarer Fokus.
- Ausreichender Kontrast (WCAG AA).
- `prefers-reduced-motion` respektieren.
- Keine Information nur über Farbe (z.B. Badge-Text + Farbe).
- Saubere Überschriftenhierarchie (h1 → h2 → h3, keine Sprünge).
- `lang="de"` im HTML-Tag.

## Performance-Ziele (Soft Targets MVP)

| Metrik | Ziel |
|---|---|
| First Contentful Paint (lokal) | < 500ms |
| Largest Contentful Paint (lokal) | < 1s |
| Time to Interactive (lokal) | < 1.5s |
| Bundle Size (kein SPA) | minimal — kein großes JS-Framework im MVP |

## Tech-Stack (geplant für M5)

- **Backend:** FastAPI + Jinja2.
- **Optional:** htmx für kleine Interaktionen.
- **Kein SPA im MVP** — keine React/Vue/Svelte-Hauptarchitektur.
- **CSS:** modernes vanilla CSS oder Tailwind (Entscheidung in M5-Tranche).
- **Markdown-Rendering:** `markdown-it-py` oder `mistune`.
- **Static Assets:** durch FastAPI ausgeliefert oder Reverse Proxy.

Begründung kein-SPA: schneller Start, geringere Komplexität, bessere Lesbarkeit, weniger JS-Bundle, einfacher zu deployen, einfacher zu cachen.

## Was bewusst _nicht_ im MVP-UI

- Komplexer Graph-View.
- Drag & Drop für Seitenstrukturen.
- Real-time Multiuser-Collaboration.
- Eigener Markdown-Editor in der UI (Obsidian reicht lokal).
- Komplexe Admin-Forms.
- Export-Funktionen (außer Markdown — schon vorhanden im Filesystem).

## Verweise

- [ARCHITECTURE_REQUIREMENTS_DOSSIER.md](ARCHITECTURE_REQUIREMENTS_DOSSIER.md) — Schicht 8/9
- [ROADMAP.md](ROADMAP.md) — M5 Web UI
- [adr/ADR-0005-web-ui-read-models.md](adr/ADR-0005-web-ui-read-models.md)
