# Curiosity Wiki

Persönliches, quellengestütztes LLM-Wissenssystem.

> **Alles darf gesammelt werden, aber nichts wird ungeprüft zur Wahrheit. Jede Quelle bleibt nachvollziehbar, jede Synthese bleibt überprüfbar, jede Agentenänderung bleibt reviewbar, und jeder produktive Stand bleibt reproduzierbar.**

## Was das ist

Das Curiosity Wiki ist ein persönlicher Wissensgarten, der drei Dinge gleichzeitig leistet:

1. **Archiv** — Interessante Rohquellen gehen nicht verloren.
2. **Synthese** — LLMs verdichten Quellen zu lesbaren, verlinkten Wiki-Seiten.
3. **Wiederentdeckung** — Das System macht alte Interessen, offene Fragen und unerwartete Verbindungen wieder sichtbar.

Es ist **kein Chatbot mit Speicher** und **kein reines RAG-System**. Es ist ein **versionierter Wissenskompiler**, der aus Quellen, Notizen, Daten und eigenen Beobachtungen stabile Wissensobjekte erzeugt.

## Architektur in einem Bild

```text
[Capture]      Browser, Webclipper, PDF, Screenshot, Notiz, Rezept, Datenimport
    │
[Raw Archive]  immutable snapshots, hashes, receipts, source policy metadata
    │
[Extraction]   extracted text, parser metadata, content fingerprints
    │
[Registry]     SQLite — sources, runs, claims, proposals, reviews, freshness, lint
    │
[LLM Proposal] drafts, diffs, new_pages, updated_pages, risk_notes, open_questions
    │
[Human Review] accept, reject, edit, quarantine, split, merge
    │
[Wiki]         Markdown pages, source pages, collections, methods, recipes
    │
[Read Models]  search docs, graph, browse cards, freshness dashboard
    │
[UI]           read-only first, später kontrollierte admin actions
```

## Status

**T0.1 — Method & Architecture Baseline.** Repo, Methodik-Dokumente, ADRs, leere Vault-Struktur, minimale CLI. Noch keine LLM-Integration, keine Web-UI, kein Deployment.

Aktuelle Tranche und nächste Schritte: siehe [docs/PROJECT_STATE.md](docs/PROJECT_STATE.md).

## Kanonische Dokumente

Vollständige Übersicht in [docs/INDEX.md](docs/INDEX.md). Wichtige Einstiege:

- **Roadmap:** [docs/ROADMAP.md](docs/ROADMAP.md)
- **Architektur:** [docs/ARCHITECTURE_REQUIREMENTS_DOSSIER.md](docs/ARCHITECTURE_REQUIREMENTS_DOSSIER.md)
- **Engineering-Regeln:** [docs/ENGINEERING_MANIFEST.md](docs/ENGINEERING_MANIFEST.md)
- **Zusammenarbeit Andreas ↔ Assistent:** [docs/WORKING_AGREEMENT.md](docs/WORKING_AGREEMENT.md)
- **Methodik-Lessons aus capsule und new_nfl:** [docs/concepts/methodik_und_lessons_learned.md](docs/concepts/methodik_und_lessons_learned.md)
- **Feinkonzept:** [docs/concepts/feinkonzept.md](docs/concepts/feinkonzept.md)

## Setup (Stand T0.1)

```powershell
# Python 3.11+ vorausgesetzt
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .[dev]

# Quality Gates
python -m pytest -q
python -m ruff check src tests tools

# CLI
python -m curiosity_wiki --help
```

## Nicht-Ziele

- Kein öffentliches Wikipedia-ähnliches Lexikon.
- Kein autonomer Webcrawler.
- Kein Archiv für Volltext-Paywall-Inhalte.
- Keine Multiuser-Collaboration im MVP.
- Keine vollautomatische Wahrheitsermittlung durch LLMs.

## Lizenz

Privates Projekt. Inhalte des Wikis dürfen ohne ausdrückliche Erlaubnis nicht weiterverwendet werden. Code-Lizenz folgt mit erstem stabilen Release.
