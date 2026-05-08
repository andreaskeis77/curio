# Lessons Learned

**Status:** Lebendes Dokument. Wird nach jeder Tranche und nach jedem signifikanten Fehler aktualisiert.
**Stand:** 2026-05-08

---

## Zweck

Lessons Learned ist **kein Schuldbuch**, sondern Methodik-Input. Wiederkehrende Fehlerklassen werden hier festgehalten, damit sie in zukünftige Tranchen einfließen können.

## Format pro Eintrag

```markdown
### YYYY-MM-DD — <Kurzname>

**Fehlerklasse:** <z.B. Compatibility Drift, Prompt Injection, Schema Drift>
**Tranche / Phase:** T<x.y> bzw. M<x>
**Was ist passiert:** <kurz>
**Root Cause / plausible Ursache:** <was war der Auslöser>
**Welche Gate-Stufe hätte es früher entdeckt?** <z.B. Stufe 3 Schema-Gate>
**Welche Regel wird angepasst?** <konkrete Änderung in Manifest, Runbook, Tests>
**Test/ADR/Runbook-Update nötig?** <Ja: ... / Nein>
```

## Bekannte Fehlerklassen (initial aus capsule und new_nfl)

### Compatibility Drift

**Beschreibung:** Schnittstellen ändern sich, abhängiger Code merkt es nicht sofort.
**Mitigation:** Contract-Tests, Schema-Versionierung, Fresh/Evolved State.

### Internal Contract Drift

**Beschreibung:** Module-interne Verträge weichen von dokumentierten ab.
**Mitigation:** Tests gegen public API, Type-Hints als Doku.

### Replay Gaps

**Beschreibung:** Run kann nicht repliziert werden, weil Prompt-/Version-/Hash-Info fehlt.
**Mitigation:** Run Evidence in Registry, Prompt Registry, Hash für Snapshots.

### Mixed Tranches

**Beschreibung:** Eine Tranche ändert zu viel auf einmal.
**Mitigation:** Tranche-Größen-Regel im Manifest, Selbst-Review im PR-Template.

### LLM Plausibility Trap

**Beschreibung:** LLM liefert plausibel klingende, aber falsche Inhalte.
**Mitigation:** Claim-Marker, Quellenbindung, Golden Tests, Confidence-Levels.

### Source Policy Late

**Beschreibung:** Erst nach problematischem Ingest gemerkt, dass Quelle nicht hätte verarbeitet werden dürfen.
**Mitigation:** Source Policy vor Capture, Policy-Felder im Manifest, Pre-Ingest-Check.

### Path Drift Windows ↔ Linux

**Beschreibung:** Code funktioniert lokal (Windows), aber nicht in CI (Linux) oder umgekehrt.
**Mitigation:** Path-Abstraktion, Tests auf beiden Plattformen, `pathlib` statt `os.path`.

### UI Reads from Wrong Layer

**Beschreibung:** UI greift direkt auf Raw oder Registry zu statt auf Read Models.
**Mitigation:** Layer-Architektur strikt durchsetzen, Code Review.

## Initiale Einträge

### 2026-05-08 — Repository-Initialisierung

**Fehlerklasse:** Keine, präventiv.
**Tranche:** T0.1
**Notiz:** Beim Setup wurde bewusst Public-Repo gewählt mit Source Policy ab Tag 0. Risiko: Versehentliches Committen privater Inhalte.

**Anwendung:**

- `.gitignore` hat `raw/**/*` ausgeschlossen (außer READMEs).
- Pre-Push-Checkliste enthält explizit Diff-Prüfung.
- `docs/SOURCE_POLICY.md` ist von Anfang an verbindlich.

---

## Antimuster-Sammlung (15 verbotene Muster)

Aus dem Engineering Manifest übernommen, hier mit kurzem Kontext:

1. **LLM schreibt direkt ins produktive Wiki.** — Verstoß gegen Layer-Architektur.
2. **Markdown-only ohne Registry.** — Operativ-Zustände werden unklar.
3. **Quellen werden überschrieben statt versioniert.** — Replay unmöglich.
4. **Zu viele Pilotdomänen im MVP.** — Breite frisst Stabilität.
5. **Web-UI erst spät und dann hektisch.** — UX wird Nachgedanke.
6. **VPS bekommt Schreibrechte zu früh.** — Sicherheitsrisiko.
7. **Prompts ändern sich ohne Version und Tests.** — Eval-Drift.
8. **Doku bleibt im Chat.** — Wissensverlust zwischen Sessions.
9. **Quality Gates werden optional.** — Rote Pfade werden übersehen.
10. **Rote operative Pfade werden schöngeredet.** — Schulden auflaufen.
11. **Private Raw Sources im Public-Bundle.** — Datenschutz-Bruch.
12. **Source Policy spät klären.** — Nachträgliches Aufräumen ist teuer.
13. **UI liest aus falscher Schicht.** — Architektur-Verletzung.
14. **Agenten zu breite Aufgaben.** — Tranche-Scope-Verstoß.
15. **Keine Fresh/Evolved State Tests.** — Evolved State bricht.

## Wann ein Eintrag nötig ist

- Wenn ein Test überraschend rot wird.
- Wenn ein Pre-Push-Check etwas verhindert hat, was leicht vergessen worden wäre.
- Wenn ein Review etwas Substantielles korrigieren musste.
- Wenn eine Tranche länger gedauert hat als geschätzt.
- Wenn ein Bug in Production eskaliert wurde.
- Wenn ein Backup/Restore-Drill etwas Unerwartetes zeigte.
- Wenn ein User-Verhalten überrascht hat.

## Wann _kein_ Eintrag nötig ist

- Tippfehler.
- Reine Formatierungs-Edits.
- Trivialer Refactor.

## Verweise

- [ENGINEERING_MANIFEST.md](ENGINEERING_MANIFEST.md) — Antimuster
- [VALIDATION_PROTOCOL.md](VALIDATION_PROTOCOL.md) — Validierung
- [PROJECT_STATE.md](PROJECT_STATE.md) — Aktuelle Lage
