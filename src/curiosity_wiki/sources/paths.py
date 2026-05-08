"""Source-Pfad-Berechnung gemäß ADR-0002.

Schema: ``raw/<source_type>/<YYYY>/<MM>/<DD>/<source_id>/<filename>``.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from curiosity_wiki.paths import VaultPaths
from curiosity_wiki.sources.models import SourceType


def source_directory(
    paths: VaultPaths,
    source_type: SourceType,
    source_id: str,
    captured_at: datetime,
) -> Path:
    """Verzeichnis, in dem alle Artefakte einer Source liegen.

    Existiert ggf. nicht — Aufrufer ist für ``mkdir`` verantwortlich.
    """
    return (
        paths.raw
        / source_type.value
        / f"{captured_at.year:04d}"
        / f"{captured_at.month:02d}"
        / f"{captured_at.day:02d}"
        / source_id
    )


def manifest_path(source_dir: Path) -> Path:
    """Pfad der ``metadata.yaml`` einer Source."""
    return source_dir / "metadata.yaml"


def hash_path(source_dir: Path) -> Path:
    """Pfad der ``content.sha256``-Beleg-Datei."""
    return source_dir / "content.sha256"
