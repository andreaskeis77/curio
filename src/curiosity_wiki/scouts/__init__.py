"""curiosity_wiki.scouts — Update-Scouts (M7, ADR-0019)."""

from __future__ import annotations

from curiosity_wiki.scouts.loader import (
    ScoutLoadError,
    discover_scouts,
    load_scout,
)
from curiosity_wiki.scouts.models import (
    ScoutDefinition,
    ScoutLimits,
    ScoutQuarantineConfig,
    ScoutSource,
    ScoutSourceType,
)
from curiosity_wiki.scouts.runner import (
    ScoutRunResult,
    run_scout,
)

__all__ = [
    "ScoutDefinition",
    "ScoutLimits",
    "ScoutLoadError",
    "ScoutQuarantineConfig",
    "ScoutRunResult",
    "ScoutSource",
    "ScoutSourceType",
    "discover_scouts",
    "load_scout",
    "run_scout",
]
