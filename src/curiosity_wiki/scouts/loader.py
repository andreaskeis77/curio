"""Scout-YAML-Loader (M7, ADR-0019).

Laedt aus ``scouts/<id>.yaml`` eine ``ScoutDefinition`` und validiert das Schema.
"""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import ValidationError

from curiosity_wiki.paths import VaultPaths, get_paths
from curiosity_wiki.scouts.models import ScoutDefinition


class ScoutLoadError(RuntimeError):
    """Konnte Scout-Definition nicht laden oder validieren."""


def _scouts_dir(paths: VaultPaths) -> Path:
    return paths.root / "scouts"


def discover_scouts(paths: VaultPaths | None = None) -> list[Path]:
    """Liefert alle Scout-YAML-Files unter ``scouts/`` in alphabetischer Reihenfolge."""
    paths = paths or get_paths()
    base = _scouts_dir(paths)
    if not base.exists():
        return []
    out: list[Path] = []
    for path in sorted(base.iterdir()):
        if path.suffix.lower() in {".yaml", ".yml"} and path.is_file():
            out.append(path)
    return out


def load_scout(scout_id: str, paths: VaultPaths | None = None) -> ScoutDefinition:
    """Laedt ``scouts/<scout_id>.yaml`` und liefert das geparste Modell."""
    paths = paths or get_paths()
    base = _scouts_dir(paths)
    candidates = [base / f"{scout_id}.yaml", base / f"{scout_id}.yml"]
    target = next((c for c in candidates if c.exists()), None)
    if target is None:
        raise ScoutLoadError(f"Scout not found: {scout_id} (searched {base})")

    try:
        payload = yaml.safe_load(target.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ScoutLoadError(f"YAML error in {target}: {exc}") from exc

    if not isinstance(payload, dict):
        raise ScoutLoadError(f"Scout file {target} must contain a mapping at top level")

    try:
        scout = ScoutDefinition.model_validate(payload)
    except ValidationError as exc:
        raise ScoutLoadError(f"Schema validation failed for {target}: {exc}") from exc

    if scout.id != scout_id:
        raise ScoutLoadError(f"Scout id mismatch: file is {target.name} but id is {scout.id!r}")
    return scout
