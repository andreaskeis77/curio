"""Manifest-IO: Source-Metadaten als YAML auf der Platte."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from curiosity_wiki.sources.models import (
    AccessType,
    CopyrightRisk,
    Reliability,
    Source,
    SourceStatus,
    SourceType,
)


def write_manifest(path: Path, source: Source) -> None:
    """Schreibt Source-Manifest als YAML.

    Atomic via temp-file + replace, damit ein Crash mitten im Schreiben
    keine kaputte Manifest-Datei hinterlässt.
    """
    payload = source.to_manifest_dict()
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.parent.mkdir(parents=True, exist_ok=True)
    text = yaml.safe_dump(payload, allow_unicode=True, sort_keys=False)
    tmp_path.write_text(text, encoding="utf-8")
    tmp_path.replace(path)


def read_manifest(path: Path) -> Source:
    """Liest ein Source-Manifest und rekonstruiert ein ``Source``-Objekt."""
    raw_text = path.read_text(encoding="utf-8")
    data: dict[str, Any] = yaml.safe_load(raw_text) or {}
    return _source_from_dict(data)


def _source_from_dict(data: dict[str, Any]) -> Source:
    return Source(
        id=str(data["id"]),
        title=data.get("title"),
        source_type=SourceType(data["source_type"]),
        original_url=data.get("original_url"),
        canonical_url=data.get("canonical_url"),
        captured_at=_parse_dt(data["captured_at"]),
        raw_path=str(data["raw_path"]),
        extracted_path=data.get("extracted_path"),
        sha256=str(data["sha256"]),
        bytes=data.get("bytes"),
        content_type=data.get("content_type"),
        language=data.get("language"),
        access=AccessType(data["access"]),
        copyright_risk=CopyrightRisk(data["copyright_risk"]),
        reliability=Reliability(data["reliability"]),
        llm_allowed=bool(data.get("llm_allowed", True)),
        status=SourceStatus(data["status"]),
        why_interesting=str(data["why_interesting"]),
        license_note=data.get("license_note"),
        created_at=_parse_dt(data["created_at"]),
        updated_at=_parse_dt(data["updated_at"]),
    )


def _parse_dt(value: object) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return datetime.fromisoformat(value)
    raise ValueError(f"Cannot parse datetime from: {value!r}")
