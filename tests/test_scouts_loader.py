"""M7 Tests: Scout-Loader und -Schema (ADR-0019)."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from curiosity_wiki.paths import VaultPaths
from curiosity_wiki.scouts import (
    ScoutDefinition,
    ScoutLoadError,
    ScoutSourceType,
    discover_scouts,
    load_scout,
)


@pytest.fixture
def vault(tmp_path: Path) -> VaultPaths:
    (tmp_path / "pyproject.toml").write_text("[project]\nname='dummy'\n", encoding="utf-8")
    return VaultPaths(root=tmp_path)


def _write_scout(vault: VaultPaths, scout_id: str, payload: dict) -> Path:
    base = vault.root / "scouts"
    base.mkdir(parents=True, exist_ok=True)
    target = base / f"{scout_id}.yaml"
    target.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return target


def test_load_minimal_scout(vault: VaultPaths) -> None:
    _write_scout(
        vault,
        "tiny",
        {
            "id": "tiny",
            "domain": "places",
            "prompt_id": "ingest_v0_1",
            "sources": [{"type": "note", "value": "hello"}],
        },
    )
    scout = load_scout("tiny", paths=vault)
    assert isinstance(scout, ScoutDefinition)
    assert scout.id == "tiny"
    assert scout.frequency_hours == 24.0  # default
    assert scout.limits.max_sources_per_run == 20
    assert scout.sources[0].type == ScoutSourceType.NOTE


def test_load_scout_with_overrides(vault: VaultPaths) -> None:
    _write_scout(
        vault,
        "deep",
        {
            "id": "deep",
            "domain": "products",
            "prompt_id": "ingest_v0_1",
            "frequency_hours": 168,
            "sources": [
                {"type": "url", "value": "https://example.org", "why_interesting": "x"},
                {"type": "note", "value": "n"},
            ],
            "limits": {"max_sources_per_run": 5, "llm_allowed": False, "dry_run": True},
            "quarantine": {"on_injection": True, "on_schema_drift": False},
        },
    )
    scout = load_scout("deep", paths=vault)
    assert scout.frequency_hours == 168
    assert scout.limits.max_sources_per_run == 5
    assert scout.limits.llm_allowed is False
    assert scout.limits.dry_run is True
    assert scout.quarantine.on_schema_drift is False


def test_load_scout_id_must_match_filename(vault: VaultPaths) -> None:
    _write_scout(
        vault,
        "filename",
        {
            "id": "different-id",
            "domain": "places",
            "prompt_id": "ingest_v0_1",
            "sources": [{"type": "note", "value": "x"}],
        },
    )
    with pytest.raises(ScoutLoadError) as exc_info:
        load_scout("filename", paths=vault)
    assert "id mismatch" in str(exc_info.value)


def test_load_scout_rejects_empty_sources(vault: VaultPaths) -> None:
    _write_scout(
        vault,
        "empty-sources",
        {
            "id": "empty-sources",
            "domain": "places",
            "prompt_id": "ingest_v0_1",
            "sources": [],
        },
    )
    with pytest.raises(ScoutLoadError):
        load_scout("empty-sources", paths=vault)


def test_load_scout_rejects_unknown_field(vault: VaultPaths) -> None:
    """extra='forbid' verhindert Tippfehler in der Konfiguration."""
    _write_scout(
        vault,
        "typo",
        {
            "id": "typo",
            "domain": "places",
            "prompt_id": "ingest_v0_1",
            "sources": [{"type": "note", "value": "x"}],
            "freqency_hours": 24,  # bewusster Tippfehler
        },
    )
    with pytest.raises(ScoutLoadError):
        load_scout("typo", paths=vault)


def test_load_scout_rejects_invalid_id_pattern(vault: VaultPaths) -> None:
    _write_scout(
        vault,
        "Bad_ID",
        {
            "id": "Bad_ID",
            "domain": "places",
            "prompt_id": "ingest_v0_1",
            "sources": [{"type": "note", "value": "x"}],
        },
    )
    with pytest.raises(ScoutLoadError):
        load_scout("Bad_ID", paths=vault)


def test_load_scout_unknown_id_raises(vault: VaultPaths) -> None:
    with pytest.raises(ScoutLoadError):
        load_scout("nonexistent", paths=vault)


def test_discover_scouts_returns_yaml_files(vault: VaultPaths) -> None:
    _write_scout(
        vault,
        "alpha",
        {
            "id": "alpha",
            "domain": "x",
            "prompt_id": "ingest_v0_1",
            "sources": [{"type": "note", "value": "x"}],
        },
    )
    _write_scout(
        vault,
        "beta",
        {
            "id": "beta",
            "domain": "x",
            "prompt_id": "ingest_v0_1",
            "sources": [{"type": "note", "value": "x"}],
        },
    )
    (vault.root / "scouts" / "ignored.txt").write_text("not a scout", encoding="utf-8")
    files = discover_scouts(paths=vault)
    names = sorted(f.stem for f in files)
    assert names == ["alpha", "beta"]


def test_discover_scouts_empty_when_dir_missing(vault: VaultPaths) -> None:
    assert discover_scouts(paths=vault) == []


def test_unesco_pilot_scout_loads_from_repo() -> None:
    """Der mitgelieferte unesco-welterbe-Scout muss schema-konform sein."""
    from curiosity_wiki.paths import get_paths

    real = get_paths()
    candidate = real.root / "scouts" / "unesco-welterbe.yaml"
    if not candidate.exists():
        pytest.skip("repo-level scout file not present")
    scout = load_scout("unesco-welterbe", paths=real)
    assert scout.id == "unesco-welterbe"
    assert len(scout.sources) >= 1
