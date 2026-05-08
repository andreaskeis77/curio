# ADR-0004: Read-only VPS first

- **Status:** Accepted
- **Datum:** 2026-05-08
- **Tranche:** T0.1

## Kontext

Das Curiosity Wiki soll auf einem Windows-VPS laufen, damit Andreas am Smartphone unterwegs lesen kann. Der VPS ist über Cloudflare Tunnel erreichbar.

Risiken bei zu früher Schreib-Funktionalität:

- **Ungewollter Public-Write-Zugriff.**
- **Backup-/Restore noch nicht erprobt.**
- **Review-Queue über Web noch nicht durchdacht.**
- **Auth/Authorization noch nicht implementiert.**
- **CSRF, Rate Limits, Upload-Validation fehlen.**

Optionen:

- **A) VPS bekommt sofort Schreibrechte** — Capture, Ingest, Review im Web.
- **B) VPS ist read-only zuerst** — Capture/Ingest/Review bleiben lokal, VPS zeigt nur freigegebene Inhalte.
- **C) VPS ist read-only mit Auth-geschützten Admin-Endpunkten.**

## Entscheidung

**Option B: VPS read-only zuerst (M6). Schreibe-Funktionen kommen frühestens nach VPS-Stabilisierung in Phase D4.**

- Web UI auf VPS liest aus `wiki/` und `read_models/`.
- **Keine** Schreibendpunkte im MVP exponiert.
- Capture, Extract, Ingest, Review bleiben **lokal** auf dem Dev-Laptop.
- Deployment ist ein einseitiger Sync von freigegebenen Inhalten.

## Begründung

- **Sicherheit:** Schreibendpunkte sind Angriffsfläche. Read-only schließt diese aus.
- **Backup-Disziplin:** Schreibrechte ohne erprobte Backups sind riskant.
- **Review-Workflow:** CLI-Review reicht für MVP. Web-Review erfordert Auth, Forms, CSRF — alles MVP-Out-of-Scope.
- **Capsule-Lesson:** Architektur und Betrieb getrennt denken; klein anfangen.
- **Vereinfachung:** VPS-Service ist Stateless für Web (Daten kommen aus Filesystem + SQLite).

## Konsequenzen

### Positiv

- Kleinere Angriffsfläche.
- Klare Verantwortungsgrenzen: lokal = schreibend, VPS = lesend.
- Einfacheres Deployment.
- Backup-Strategie kann erst lokal reifen.

### Negativ

- **Eingeschränkte Mobile-Nutzung initial:** Andreas kann unterwegs lesen, aber nicht capturen.
- **Capture-Workflow erfordert Laptop** — keine ad-hoc Smartphone-Erfassung im MVP.

### Risiken und Mitigationen

| Risiko | Mitigation |
|---|---|
| Mobile Capture wäre praktisch | Workaround: Notiz-App + später lokal nachpflegen |
| VPS-Inhalt wird stale ohne Sync | Deployment-Skript läuft regelmäßig |
| Versehentliches Aktivieren von Schreibendpunkten | Code-Konstante `WRITE_ENABLED=False`, kein Fallback |

## Schritte zur späteren Schreib-Funktionalität (Phase D4)

1. Auth-Modell (Token, Basic Auth oder OAuth) entscheiden.
2. CSRF-Schutz implementieren.
3. Audit-Log für Schreibendpunkte.
4. Rate Limits.
5. Upload-Validation (Größe, Typ, Virusscan).
6. Review-UI getestet.
7. Backup-Drill mit Schreib-Workload.
8. ADR-Update / neues ADR.

## Verweise

- [ARCHITECTURE_REQUIREMENTS_DOSSIER.md](../ARCHITECTURE_REQUIREMENTS_DOSSIER.md) §8
- [SECURITY.md](../SECURITY.md)
- [ROADMAP.md](../ROADMAP.md) — M6
- [concepts/methodik_und_lessons_learned.md](../concepts/methodik_und_lessons_learned.md) §10
