# Source Policy

**Status:** v0.1
**Stand:** 2026-05-08

Welche Quellen wie gespeichert, klassifiziert und verarbeitet werden dürfen.

---

## Grundsatz

> Alles darf gesammelt werden, aber nicht alles darf gespeichert, weiterverarbeitet oder veröffentlicht werden.

Eine Quelle wird nicht erst nach problematischem Ingest geklärt — sondern **vor** dem Ingest.

## Quellen-Klassen

### Access

| Wert | Bedeutung |
|---|---|
| `public` | Frei zugängliche Quelle ohne Login. |
| `private` | Eigene Notiz, eigene Aufzeichnung, eigene Beobachtung. |
| `paywalled` | Hinter Bezahlschranke. **Kein Volltext-Speichern.** |
| `own_note` | Eigene Methode/Rezept/Experiment-Notiz. |

### Copyright Risk

| Wert | Bedeutung |
|---|---|
| `low` | Eigene Inhalte, klare Public-Domain, offizielle Statistik. |
| `medium` | Journalistische Artikel, Blog-Beiträge, Wikipedia. |
| `high` | Bezahlte Test-Berichte, urheberrechtlich geschützte Werke, Bilder mit unklarer Lizenz. |

### Reliability

| Wert | Bedeutung |
|---|---|
| `official` | UNESCO, Behörden, offizielle Hersteller-Doku. |
| `expert` | Fachartikel, Forschungs-Output, anerkannte Spezialisten. |
| `journalistic` | Tageszeitung, Magazin, Online-Redaktion. |
| `commercial` | Hersteller-Marketing, Werbung. |
| `personal` | Eigene Notizen, eigene Erfahrungen. |
| `unknown` | Unbekannte Reliability — wird im Wiki sichtbar. |

### LLM Allowed

| Wert | Bedeutung |
|---|---|
| `true` | Quelle darf für LLM-Synthese genutzt werden. |
| `false` | Nur Link + eigene Notizen, kein Volltext an LLM. |

## Speicher-Regeln

| Quelle | Raw Speichern? | Extracted Speichern? | LLM-Synthese? |
|---|---|---|---|
| Public Wikipedia-Artikel | ja (Snapshot) | ja | ja |
| UNESCO offizielle Seite | ja | ja | ja |
| Fachartikel (Public) | ja | ja | ja |
| Bezahlter Testbericht | **nein** (nur Link + Notizen) | nein | **nein** |
| Paywall-Artikel | **nein** | nein | **nein** |
| Eigene Notiz | ja | ja (= Notiz selbst) | ja |
| Eigenes Rezept-Experiment | ja | ja | ja |
| Screenshot eines Werks | nur lokal | nein | **nein** |
| Hersteller-Datenblatt | ja | ja | ja (mit Vorsicht: Marketing!) |

## Ingest-Regeln

### Bei `paywalled` oder `copyright_risk: high`

- Quelle wird **nicht** als Volltext extrahiert.
- Stattdessen: Link, Titel, Autor, Datum, eigene Notiz.
- Wiki-Seite enthält Verweis auf Quelle, aber **keine zitierten Volltexte**.
- LLM erhält keinen Volltext, nur eigene Notizen + Quellen-Metadaten.

### Bei `private` oder `own_note`

- Bleibt lokal in `raw/`.
- Geht **nie** in das Public-Bundle.
- Kann in lokales Wiki kuratiert werden.

### Bei `public` und `low` Risk

- Vollständige Pipeline: Capture → Extract → Ingest → Review → Publish.
- Source Page kann veröffentlicht werden.

## Quarantäne-Auslöser

Eine Quelle geht in Quarantäne, wenn:

- Sie **Prompt-Injection-artige** Anweisungen enthält.
- Ihre **Reliability** unklar ist und **Copyright Risk** hoch.
- Sie **widersprüchliche Daten** zur bestehenden Wiki-Synthese liefert.
- Ihre **Extraktion** offensichtlich kaputt ist.
- Sie **Duplikat** einer existierenden Quelle ohne wesentliche Neuerung ist.

Quarantäne-Einträge in Registry (`quarantine_cases`):

```yaml
case_id: q_20260507_001
case_type: extraction_failed | source_policy_risk | prompt_injection | claim_unverified | duplicate_page | stale_volatile_page
severity: low | medium | high
source_id: src_...
status: open | resolved | suppressed | archived
recommended_action: "Quelle manuell prüfen und nur Link + eigene Notizen übernehmen."
```

## Veröffentlichungs-Regeln (ab M6 VPS)

Auf dem öffentlichen VPS landen:

- ✅ Kuratierte Wiki-Seiten (Markdown + Read Models).
- ✅ Source Pages mit `access: public` und `copyright_risk: low/medium`.
- ✅ Eigene Synthesen, eigene Notizen, eigene Experimente.

Nicht auf dem VPS:

- ❌ Raw Snapshots privater oder paywalled Quellen.
- ❌ Original-Volltexte urheberrechtlich geschützter Werke.
- ❌ Screenshots geschützter Inhalte.
- ❌ Persönliche Notizen, die Andreas privat halten möchte.

Pre-Deploy-Filter:

```text
- copyright_risk >= medium → Volltext nicht im Bundle
- access in (private, paywalled) → Source Page nicht im Bundle
- llm_allowed == false → keine LLM-erzeugten Inhalte aus dieser Quelle
- Source Page ohne Manifest → ausschließen
```

## Pilot-Bereiche und Source Policy

| Pilot | Erwartete Quellen | Risiken |
|---|---|---|
| **UNESCO** | Offizielle UNESCO-Seiten, Wikipedia, Fachliteratur | meist low/medium, Bilder mit Vorsicht |
| **Pacojet** | Eigene Notizen, Hersteller-Doku, Fachartikel | low (eigene), medium (Hersteller) |
| **Produkttests** (später) | Eigene Recherche, Hersteller-Specs, Tests | **hoch** — keine Volltext-Tests, nur eigene Notizen + Links |
| **Haute Couture** (später) | Wikipedia, offene Mode-Archive, eigene Beobachtungen | medium, Bilder mit Vorsicht |

## Lizenzhinweis pro Quelle

Wo nötig, im Manifest:

```yaml
license_note: "Nur private Nutzung; keine Volltext-Veröffentlichung."
```

Diese Notiz wird im Filter ausgewertet und blockiert das Aufnehmen der Quelle in das Public-Bundle.

## Bei rechtlichen Anfragen

- Quelle aus `raw/` entfernen (lokale Kopie).
- Source Page in Wiki anonymisieren oder entfernen.
- Eintrag in `docs/_ops/restore_drills/` (oder `incidents/`) dokumentieren.
- Bei Veröffentlichung auf VPS: Republish ohne entfernte Inhalte.

## Verweise

- [SECURITY.md](SECURITY.md)
- [ARCHITECTURE_REQUIREMENTS_DOSSIER.md](ARCHITECTURE_REQUIREMENTS_DOSSIER.md)
- [adr/ADR-0002-immutable-raw-sources.md](adr/ADR-0002-immutable-raw-sources.md)
- [adr/ADR-0006-source-policy-and-copyright-boundaries.md](adr/ADR-0006-source-policy-and-copyright-boundaries.md)
