# Lessons Learned

**Status:** Lebendes Dokument. Wird nach jeder Tranche und nach jedem signifikanten Fehler aktualisiert.
**Stand:** 2026-05-10

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

### 2026-05-10 — `.gitignore`-Pfade Singular vs. Plural

**Fehlerklasse:** Source Policy Late (latent), Path Drift.
**Tranche:** M6e.
**Was ist passiert:** Beim ersten echten `curiosity capture note` fielen `raw/note/<id>/` an. `git status` zeigte sie als _untracked_, weil `.gitignore` als Pattern `raw/notes/*` (Plural) hatte — die echten Pfade folgen aber `SourceType.value` und sind Singular (`note`, `screenshot`). `raw/file/*` war komplett vergessen. Hätte ein blindes `git add .` private Notiz-Snapshots ins Public-Repo geschoben.
**Root Cause:** `.gitignore` wurde in T0.1 vor der Pipeline geschrieben und nie gegen die echten `SourceType.value`-Pfade verifiziert.
**Welche Gate-Stufe hätte es früher entdeckt?** Stufe 1 (Pre-Push-Diff) hätte es zwar abgefangen, aber nur _wenn_ man hinschaut. Idealere Gate: ein Test, der für jeden `SourceType.value` prüft, dass der Pfad ignored ist.
**Welche Regel wird angepasst?** `.gitignore` korrigiert (Singular + `raw/file/*`). In Phase A: ein Test in `tests/test_source_policy.py`, der für jeden `SourceType.value` `git check-ignore` aufruft. Die Pre-Push-Checkliste bleibt zusätzlich.
**Test/ADR/Runbook-Update nötig?** Test-Eintrag in Phase-A-Roadmap; kein ADR.

### 2026-05-10 — Manuelle Wiki-Pages haben keinen Pfad in die `pages`-Tabelle

**Fehlerklasse:** Internal Contract Drift.
**Tranche:** M6e.
**Was ist passiert:** Die zwei manuellen Pilot-Pages (`alhambra.md`, `pacojet.md`) konnte ich nur über einen ad-hoc Helper `_tmp_register_manual_pages.py` in die Registry bringen. `curiosity index rebuild` schreibt nur `pages_fts`, nicht `pages`/`page_sources`/`links`. Ohne den Helper waren die Pages weder im Web-UI (`/p/<slug>` queryt `pages`) noch in den Read-Models sichtbar.
**Root Cause:** Der Publish-Workflow ist ausschließlich Proposal-getrieben (M3) — manuelle Markdown-Authoring ist als Use-Case da, aber der Pfad in die DB war nicht implementiert. Phase A ROADMAP nennt das bereits („Registry-Rebuild aus Markdown").
**Welche Regel wird angepasst?** Phase A bekommt ein konkretes Item: `curiosity registry import-md` (volle Round-Trip-CLI inkl. `links`-Re-Resolve). Der `_tmp_register_manual_pages.py`-Helper wurde nach dem Lauf gelöscht — der Code lebt im Handoff vom 2026-05-10 als Referenz.
**Test/ADR/Runbook-Update nötig?** Phase-A-Roadmap-Item, kleiner ADR sobald die CLI gebaut wird (Atomic-Insert-Strategie, Konflikt mit M3-Publish auf gleichem Slug).

### 2026-05-10 — Bundle-Push-Transport-Marathon

**Fehlerklasse:** Operational, "Last Mile".
**Tranche:** M6e Live-Deploy.
**Was ist passiert:** Bundle vom Laptop auf vmd193069 zu schieben hat 4 Anläufe gebraucht: SMB ohne Creds (Auth-Fail), SMB mit `Administrator` (Netzwerkname-Fehler — falscher User), SMB mit `srv-ops-admin` (Netzwerkname-Fehler — `srv-ops-admin` ist nicht in der lokalen `Administrators`-Gruppe und kommt deshalb nicht an `c$`), RDP-Drive-Redirection (`mstsc /v:` springt direkt zum Login und zeigt den „Lokale Ressourcen → Mehr"-Dialog gar nicht), `tailscale file cp` (in Tailscale 1.96 entfernt). Erfolgreich war erst Anlauf 5: `python -m http.server` auf dem Laptop, `Invoke-WebRequest` von der VPS über die Tailscale-IP.
**Root Cause:** Der RUNBOOK-Beispielblock dokumentierte SMB als _den_ Pfad, ohne die zwei harten Voraussetzungen (lokaler Admin, c$-Adminshare aktiv) zu nennen — und ohne einen Backup-Plan für die häufigen Fälle, in denen das nicht erfüllt ist (geteiltes Service-Admin-Konto, Group-Policy gegen Admin-Shares, RDP-Restrict).
**Welche Regel wird angepasst?**
- RUNBOOK §"Pro Deploy" um drei Transport-Optionen erweitert: SMB (wenn Admin-Share-Zugriff da ist), RDP-Drive-Redirection (wenn Group-Policy es erlaubt), HTTPS-Pull über Tailscale-IP (always works). Reihenfolge: HTTPS-Pull als Default, SMB nur wenn als Convenience eingerichtet.
- Phase A bekommt ein `scripts/push-bundle-to-vps.ps1`-Item: probiert die Pfade durch, baut bei Bedarf den HTTP-Server temporär auf dem Laptop, räumt sauber ab. Damit ist der Push einbeinig statt fünfbeinig.
**Test/ADR/Runbook-Update nötig?** RUNBOOK heute aktualisiert; Phase-A-Skript folgt; kein ADR.

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
