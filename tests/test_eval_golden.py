"""M4 Tests: Golden-Questions-Runner."""

from __future__ import annotations

import shutil
from collections.abc import Iterator
from pathlib import Path

import pytest

from curiosity_wiki.evals import run_golden_questions
from curiosity_wiki.paths import VaultPaths, get_paths
from curiosity_wiki.registry import connect, migrate


@pytest.fixture
def vault(tmp_path: Path) -> VaultPaths:
    (tmp_path / "pyproject.toml").write_text("[project]\nname='dummy'\n", encoding="utf-8")
    real_root = get_paths().root
    # Goldens unter eval/ kopieren — die werden vom Runner relativ zum Vault gelesen.
    eval_src = real_root / "eval"
    if eval_src.exists():
        shutil.copytree(eval_src, tmp_path / "eval")
    real_prompts = get_paths().prompts
    if real_prompts.exists():
        shutil.copytree(real_prompts, tmp_path / "prompts")
    return VaultPaths(root=tmp_path)


@pytest.fixture
def conn(vault: VaultPaths) -> Iterator:
    with connect(vault.registry_db) as connection:
        migrate(connection)
        yield connection


def test_golden_questions_all_pass_on_empty_wiki(vault: VaultPaths, conn) -> None:
    """Strukturelle Goldens muessen auch auf leerem Wiki gruen sein."""
    run = run_golden_questions(conn, paths=vault)
    failed_ids = [r.id for r in run.results if not r.passed]
    assert run.failed == 0, (
        f"failed: {failed_ids}; details: {[r.detail for r in run.results if not r.passed]}"
    )
    assert run.total >= 10  # ROADMAP fordert >= 10 Fragen


def test_golden_invalid_filter_question_handled(vault: VaultPaths, conn) -> None:
    """Eine Frage mit expect_error=SearchError muss das als Pass werten."""
    run = run_golden_questions(conn, paths=vault)
    invalid_filter = next(r for r in run.results if r.id == "gq_search_invalid_filter_handled")
    assert invalid_filter.passed
    assert "SearchError" in invalid_filter.detail
