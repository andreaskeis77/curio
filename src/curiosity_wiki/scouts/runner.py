"""Scout-Runner (M7, ADR-0019).

Stub fuer M7a — die volle Pipeline (Lock-File, Run-Log, capture/extract/ingest)
folgt in M7b. Hier nur das Daten-Modell fuer das Run-Ergebnis, damit
Konsumenten (CLI, Tests) den Typ schon importieren koennen.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ScoutRunResult:
    """Ergebnis eines Scout-Laufs."""

    run_id: str
    scout_id: str
    status: str  # running | completed | skipped | failed | crashed
    sources_seen: int = 0
    captured: int = 0
    skipped: int = 0
    proposals: int = 0
    quarantined: int = 0
    errors: int = 0
    log_path: str | None = None
    error_message: str | None = None
    proposal_ids: list[str] = field(default_factory=list)


def run_scout(scout_id: str, **_: object) -> ScoutRunResult:
    """Ausfuehrungs-Stub. Volle Implementierung in M7b."""
    raise NotImplementedError("Scout-Runner is implemented in M7b.")
