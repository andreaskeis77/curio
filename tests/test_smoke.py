"""Smoke tests — sicherstellen, dass das Paket überhaupt lädt.

Plus M4-E2E-Smoke: capture -> extract -> ingest -> approve -> search.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

import curiosity_wiki
from curiosity_wiki.config import CuriosityConfig
from curiosity_wiki.extraction import extract_source
from curiosity_wiki.paths import VaultPaths, get_paths
from curiosity_wiki.proposals import ingest_source
from curiosity_wiki.registry import connect, migrate
from curiosity_wiki.search import search_pages
from curiosity_wiki.sources import capture_note
from curiosity_wiki.wiki import publish_proposal


def test_package_imports() -> None:
    assert hasattr(curiosity_wiki, "__version__")


def test_version_is_string() -> None:
    assert isinstance(curiosity_wiki.__version__, str)
    assert curiosity_wiki.__version__.count(".") >= 2


def test_e2e_smoke_capture_to_search(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """M4-Akzeptanz: nach Approve findet 'search' die publizierte Page."""
    (tmp_path / "pyproject.toml").write_text("[project]\nname='dummy'\n", encoding="utf-8")
    real = get_paths().prompts
    if real.exists():
        shutil.copytree(real, tmp_path / "prompts")
    vault = VaultPaths(root=tmp_path)
    monkeypatch.setenv("CURIOSITY_VAULT_ROOT", str(tmp_path))

    config = CuriosityConfig(
        llm_provider="mock",
        llm_model="",
        llm_temperature=0,
        llm_timeout_seconds=30,
        log_level="INFO",
        log_format="text",
        web_host="127.0.0.1",
        web_port=8765,
        dev_fail_fast=True,
        agent_dry_run=True,
    )

    with connect(vault.registry_db) as conn:
        migrate(conn)
        source = capture_note(
            "Eine eigenwillige Notiz ueber Curiosity, voller Stichworte zum Indexieren.",
            why_interesting="E2E-Smoke",
            conn=conn,
            paths=vault,
        )
        extract_source(source.id, conn=conn, paths=vault)
        ingest_result = ingest_source(source.id, conn=conn, paths=vault, config=config)
        assert ingest_result.proposal_id is not None
        publish_result = publish_proposal(
            ingest_result.proposal_id, conn=conn, paths=vault, auto_commit=False
        )
        assert publish_result.pages_written, "expected at least one page written"

        # Mock-Provider liefert Default-Page mit Title 'Mock Topic' und Body
        # 'Mock-generierter Standardinhalt.' — beides muss FTS finden.
        hits = search_pages(conn, "Mock")
        titles = [h.title for h in hits]
        assert "Mock Topic" in titles, f"expected 'Mock Topic' among {titles}"
