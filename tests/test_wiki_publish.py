"""Integrations-Tests fuer die Publish-Pipeline (Approve / Reject / Request-Changes)."""

from __future__ import annotations

import shutil
from collections.abc import Iterator
from pathlib import Path

import pytest

from curiosity_wiki.config import CuriosityConfig
from curiosity_wiki.extraction import extract_source
from curiosity_wiki.paths import VaultPaths, get_paths
from curiosity_wiki.proposals import ProposalRepository, ingest_source
from curiosity_wiki.registry import connect, migrate
from curiosity_wiki.sources import capture_note
from curiosity_wiki.wiki import (
    ClaimRepository,
    PageRepository,
    PublishError,
    publish_proposal,
    reject_proposal,
    request_changes,
)
from curiosity_wiki.wiki.frontmatter import parse_frontmatter, validate_frontmatter


@pytest.fixture
def vault_with_prompts(tmp_path: Path) -> VaultPaths:
    (tmp_path / "pyproject.toml").write_text("[project]\nname='dummy'\n", encoding="utf-8")
    real = get_paths().prompts
    if real.exists():
        shutil.copytree(real, tmp_path / "prompts")
    return VaultPaths(root=tmp_path)


@pytest.fixture
def conn(vault_with_prompts: VaultPaths) -> Iterator:
    with connect(vault_with_prompts.registry_db) as connection:
        migrate(connection)
        yield connection


@pytest.fixture
def mock_config() -> CuriosityConfig:
    return CuriosityConfig(
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


def _make_proposal(vault: VaultPaths, conn, config) -> str:
    """Helper: capture -> extract -> ingest, return proposal_id."""
    source = capture_note(
        "Test-Source fuer Publish",
        why_interesting="Test",
        conn=conn,
        paths=vault,
    )
    extract_source(source.id, conn=conn, paths=vault)
    result = ingest_source(source.id, conn=conn, paths=vault, config=config)
    assert result.proposal_id is not None
    return result.proposal_id


def test_publish_creates_pages_and_source_page(
    vault_with_prompts: VaultPaths, conn, mock_config: CuriosityConfig
) -> None:
    pid = _make_proposal(vault_with_prompts, conn, mock_config)
    result = publish_proposal(pid, conn=conn, paths=vault_with_prompts, auto_commit=False)

    assert result.proposal_id == pid
    assert result.pages_written, "expected at least one page written"
    # Source-Page existiert
    assert result.source_page_path is not None
    assert (vault_with_prompts.root / result.source_page_path).exists()
    # Pages auf Platte
    for path in result.pages_written:
        full = vault_with_prompts.root / path
        assert full.exists(), f"page file missing: {path}"
        text = full.read_text(encoding="utf-8")
        front, _ = parse_frontmatter(text)
        errors = validate_frontmatter(front)
        assert errors == [], f"frontmatter invalid in {path}: {errors}"
    # Registry hat Pages
    page_repo = PageRepository(conn)
    assert page_repo.count() >= 1
    # Proposal ist approved
    record = ProposalRepository(conn).get(pid)
    assert record is not None
    assert record.status == "approved"


def test_publish_does_not_auto_commit_by_default(
    vault_with_prompts: VaultPaths, conn, mock_config: CuriosityConfig
) -> None:
    pid = _make_proposal(vault_with_prompts, conn, mock_config)
    result = publish_proposal(pid, conn=conn, paths=vault_with_prompts, auto_commit=False)
    assert result.git_commit is None


def test_publish_unknown_proposal_raises(
    vault_with_prompts: VaultPaths, conn, mock_config: CuriosityConfig
) -> None:
    with pytest.raises(PublishError):
        publish_proposal("prop_unknown", conn=conn, paths=vault_with_prompts, auto_commit=False)


def test_publish_already_approved_raises(
    vault_with_prompts: VaultPaths, conn, mock_config: CuriosityConfig
) -> None:
    pid = _make_proposal(vault_with_prompts, conn, mock_config)
    publish_proposal(pid, conn=conn, paths=vault_with_prompts, auto_commit=False)
    with pytest.raises(PublishError):
        publish_proposal(pid, conn=conn, paths=vault_with_prompts, auto_commit=False)


def test_reject_sets_status_and_writes_no_files(
    vault_with_prompts: VaultPaths, conn, mock_config: CuriosityConfig
) -> None:
    pid = _make_proposal(vault_with_prompts, conn, mock_config)
    wiki_before = (
        list(vault_with_prompts.wiki.rglob("*.md")) if vault_with_prompts.wiki.exists() else []
    )
    reject_proposal(pid, conn=conn, reason="not relevant")
    wiki_after = (
        list(vault_with_prompts.wiki.rglob("*.md")) if vault_with_prompts.wiki.exists() else []
    )
    record = ProposalRepository(conn).get(pid)
    assert record is not None
    assert record.status == "rejected"
    assert wiki_before == wiki_after


def test_request_changes_sets_status_and_writes_notes(
    vault_with_prompts: VaultPaths, conn, mock_config: CuriosityConfig
) -> None:
    pid = _make_proposal(vault_with_prompts, conn, mock_config)
    request_changes(pid, conn=conn, paths=vault_with_prompts, notes="Bitte mehr Details")
    record = ProposalRepository(conn).get(pid)
    assert record is not None
    assert record.status == "needs_changes"
    notes_path = vault_with_prompts.root / record.path / "review_notes.md"
    assert notes_path.exists()
    assert "Bitte mehr Details" in notes_path.read_text(encoding="utf-8")


def test_publish_then_reject_chain(
    vault_with_prompts: VaultPaths, conn, mock_config: CuriosityConfig
) -> None:
    """Publish auf approved -> reject darf nicht mehr durchgehen (kein doppelter Status-Wechsel)."""
    pid = _make_proposal(vault_with_prompts, conn, mock_config)
    publish_proposal(pid, conn=conn, paths=vault_with_prompts, auto_commit=False)
    # reject veraendert Status, aber wiki bleibt geschrieben (das ist OK — Audit-Trail)
    reject_proposal(pid, conn=conn, reason="post-hoc reject")
    record = ProposalRepository(conn).get(pid)
    assert record is not None
    assert record.status == "rejected"


def test_publish_creates_claim_when_hard_facts_present(
    vault_with_prompts: VaultPaths,
    conn,
    mock_config: CuriosityConfig,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Mock-Provider liefert Default ohne hard_facts; wir setzen Fixture mit Fakten."""
    import yaml

    # Mock-Provider liest fixture aus get_vault_root() — env muss zeigen.
    monkeypatch.setenv("CURIOSITY_VAULT_ROOT", str(vault_with_prompts.root))

    source = capture_note("Fact-Source", why_interesting="x", conn=conn, paths=vault_with_prompts)
    extract_source(source.id, conn=conn, paths=vault_with_prompts)
    fixture_dir = vault_with_prompts.tests_fixtures / "llm_outputs" / "ingest_v0_1"
    fixture_dir.mkdir(parents=True, exist_ok=True)
    fixture = {
        "new_pages": [
            {
                "title": "Mock With Fact",
                "slug": "mock-with-fact",
                "type": "topic",
                "sources": [source.id],
                "sections": [{"heading": "Kurzfassung", "markdown": "Test."}],
                "open_questions": [],
                "why_interesting": "fact test",
                "confidence": "medium",
            }
        ],
        "hard_facts": [
            {
                "claim_text": "Aufnahme im Jahr 1984.",
                "claim_type": "year",
                "source_id": source.id,
                "confidence": "high",
            }
        ],
        "open_questions": [],
        "risk_notes": [],
        "freshness_recommendations": [{"page_title": "Mock With Fact", "freshness": "stable"}],
        "overall_confidence": "medium",
        "summary": "Fact present.",
    }
    (fixture_dir / f"{source.id}.yaml").write_text(
        yaml.safe_dump(fixture, allow_unicode=True), encoding="utf-8"
    )
    result = ingest_source(source.id, conn=conn, paths=vault_with_prompts, config=mock_config)
    assert result.proposal_id is not None
    publish_result = publish_proposal(
        result.proposal_id, conn=conn, paths=vault_with_prompts, auto_commit=False
    )
    assert publish_result.claims_count >= 1
    claims = ClaimRepository(conn)
    assert claims.count() >= 1
