# Security

**Status:** v0.1
**Stand:** 2026-05-08

---

## Bedrohungsmodell

| Bedrohung | Auswirkung | Wahrscheinlichkeit | Gegenmaßnahme |
|---|---|---|---|
| Prompt Injection in Webquellen | Agent ausgetrickst, falsche Synthese | hoch | Untrusted-Source-Pattern, Quarantäne |
| LLM API Key Leak | Kosten, Missbrauch | mittel | `.env` gitignore, Secret Scan |
| Private Raw Sources im Public Repo | Datenschutz, Copyright | mittel | `raw/**/*` gitignore, Secret Scan |
| Ungewollter Public-VPS-Zugriff | Privatsphäre | niedrig | Cloudflare Tunnel, kein offener Port |
| Agent schreibt in `wiki/` ohne Review | Falsche Inhalte | mittel (ohne Schutz) | Proposal-only Pattern |
| Wiki-Inhalte enthalten Halluzinationen | Persönliche Wissensbasis verfälscht | hoch | Claim-Marker, Golden Tests, Confidence-Levels |
| Backup verloren | Datenverlust | niedrig | Lokales Backup + Restore-Drill |
| RDP von außen | Server-Übernahme | niedrig (mit Tailscale) | Tailscale-only RDP |

## Geheimnis-Klassen

| Klasse | Beispiel | Speicherort |
|---|---|---|
| **API Keys** | `ANTHROPIC_API_KEY`, `OPENAI_API_KEY` | `.env` (lokal, gitignored) |
| **VPS Auth Tokens** | `CURIOSITY_WEB_AUTH_TOKEN` | `.env` auf VPS, separat von Dev-Laptop |
| **Cloudflare Credentials** | Tunnel-Token | OS-Credential-Store oder `cloudflared.yml` (gitignored) |
| **Tailscale Credentials** | Auth-Key | Per Tailscale CLI gespeichert |
| **Backup Encryption Keys** | falls genutzt | OS-Credential-Store |

## Regeln

### `.env` und Secrets

- **Nie** committen.
- `.env` immer in `.gitignore`.
- `.env.example` als Vorlage ohne echte Werte.
- Secret Scan im Quality Gate.
- API-Key-Rotation alle 6 Monate (oder bei Verdacht).

### Raw Sources

- **Default:** privat, lokal, nicht im Public-Repo.
- `raw/**/*` ist in `.gitignore`.
- Nur READMEs und explizit unkritische Beispiel-Fixtures gehen ins Repo.
- Klassifizierung pro Quelle in Manifest-Frontmatter:
  - `access: public | private | paywalled | own_note`
  - `copyright_risk: low | medium | high`

### LLM-Calls

- Untrusted Source: Quellen-Inhalt wird **nie** als Anweisung interpretiert.
- System-Prompts bleiben getrennt vom Quellen-Inhalt.
- Keine Shell-Kommandos aus Quellen ausführen.
- Keine URLs aus Quellen automatisch aufrufen (außer Update Scouts mit explizitem Whitelist).
- Keine Secrets in LLM-Kontext geben.

### Agent Permissions

| Bereich | Lese-Zugriff | Schreib-Zugriff |
|---|---|---|
| `raw/` | ja | nur Capture-Adapter |
| `extracted/` | ja | nur Extraction-Pipeline |
| `wiki/` | ja | nur Publish nach Review |
| `proposals/` | ja | Agenten dürfen schreiben |
| `data/registry/` | ja (über CLI) | nur transaktionale Tools |
| `scripts/` | nur lesend | keine Agentenänderung ohne PR |
| `.env` / Secrets | **nein** | **nein** |

### VPS

- Cloudflare Tunnel für öffentlichen Zugang.
- Kein RDP-Port öffentlich.
- Tailscale für Admin-RDP.
- Windows Firewall: eingehend nur, was nötig ist.
- Keine LLM-Calls vom VPS aus im MVP.
- Keine Schreibrechte für Web-UI im MVP.

## Pre-Push-Checkliste

Vor jedem Push:

- [ ] `.env` nicht im Diff.
- [ ] Keine Pfade aus `raw/` (außer READMEs) im Diff.
- [ ] Secret Scan grün.
- [ ] Keine API-Keys, Tokens, Passwörter in Strings.
- [ ] Keine private Quellen-IDs in Public-Doku.

```powershell
git status --short
git diff --cached
python tools/secret_scan.py --mode tracked
```

## Pre-Deploy-Checkliste (ab M6)

Zusätzlich zu Pre-Push:

- [ ] Publish-Bundle enthält keine privaten Raw Sources.
- [ ] Publish-Bundle enthält keine `.env` oder Secrets.
- [ ] Health-Endpunkt antwortet.
- [ ] TLS-Konfiguration (Cloudflare) korrekt.
- [ ] Backup vor Deploy.

## Bei Verdacht auf Secret-Leak

1. **Sofort:** Key bei Provider widerrufen.
2. Neue Keys erzeugen.
3. Lokale `.env` aktualisieren.
4. Falls auf VPS: `.env` dort aktualisieren, Service restart.
5. Git-Historie prüfen — falls in History, mit `git filter-repo` entfernen und force-push (nur auf privatem Repo!).
6. In LESSONS_LEARNED dokumentieren.

## Bei Verdacht auf Prompt Injection

1. Quelle zu Quarantäne.
2. Proposal markieren als `risk: prompt_injection`.
3. Nicht in Wiki publizieren.
4. Quarantäne-Eintrag mit Severity in Registry.
5. Beispiel als Fixture in `tests/fixtures/sources/prompt_injection_<n>.md` ablegen.

## Verweise

- [SOURCE_POLICY.md](SOURCE_POLICY.md) — Quellen-Klassifizierung
- [ARCHITECTURE_REQUIREMENTS_DOSSIER.md](ARCHITECTURE_REQUIREMENTS_DOSSIER.md) — Sicherheits-Architektur
- [adr/ADR-0006-source-policy-and-copyright-boundaries.md](adr/ADR-0006-source-policy-and-copyright-boundaries.md)
