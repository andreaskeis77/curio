"""Tests für die Path-Abstraktion."""

from __future__ import annotations

from pathlib import Path

import pytest

from curiosity_wiki.paths import VaultPaths, get_paths, get_vault_root


def test_vault_root_is_path() -> None:
    root = get_vault_root()
    assert isinstance(root, Path)


def test_vault_root_is_absolute() -> None:
    root = get_vault_root()
    assert root.is_absolute()


def test_vault_root_contains_pyproject() -> None:
    root = get_vault_root()
    assert (root / "pyproject.toml").exists()


def test_get_paths_returns_vault_paths() -> None:
    p = get_paths()
    assert isinstance(p, VaultPaths)


def test_paths_all_named_keys() -> None:
    p = get_paths()
    named = p.all_named()
    expected_keys = {
        "root",
        "docs",
        "raw",
        "extracted",
        "proposals",
        "wiki",
        "read_models",
        "registry_dir",
        "registry_db",
        "prompts",
        "eval",
        "tests_fixtures",
        "ops_logs",
    }
    assert expected_keys <= named.keys()


def test_paths_are_consistent() -> None:
    p = get_paths()
    assert p.docs == p.root / "docs"
    assert p.raw == p.root / "raw"
    assert p.wiki == p.root / "wiki"
    assert p.registry_db == p.registry_dir / "curiosity.sqlite"


def test_vault_root_override(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("CURIOSITY_VAULT_ROOT", str(tmp_path))
    root = get_vault_root()
    assert root == tmp_path.resolve()
