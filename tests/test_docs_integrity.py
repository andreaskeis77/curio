"""Doku-Integritäts-Tests.

Prüft, dass die kanonischen Dokumente existieren und sinnvolle Anker enthalten.
Diese Tests fangen versehentliche Löschungen oder Renames früh ab.
"""

from __future__ import annotations

import pytest

from curiosity_wiki.paths import get_paths

CANONICAL_DOCS = [
    "INDEX.md",
    "PROJECT_STATE.md",
    "ROADMAP.md",
    "ARCHITECTURE_REQUIREMENTS_DOSSIER.md",
    "ENGINEERING_MANIFEST.md",
    "WORKING_AGREEMENT.md",
    "DELIVERY_PROTOCOL.md",
    "VALIDATION_PROTOCOL.md",
    "TEST_STRATEGY.md",
    "RELEASE_PROCESS.md",
    "RUNBOOK.md",
    "SECURITY.md",
    "SOURCE_POLICY.md",
    "UI_UX_GUIDE.md",
    "PROMPT_REGISTRY.md",
    "EVAL_STRATEGY.md",
    "LESSONS_LEARNED.md",
]

ADRS = [
    "ADR-0001-markdown-plus-sqlite-registry.md",
    "ADR-0002-immutable-raw-sources.md",
    "ADR-0003-agent-proposals-not-direct-writes.md",
    "ADR-0004-read-only-vps-first.md",
    "ADR-0005-web-ui-read-models.md",
    "ADR-0006-source-policy-and-copyright-boundaries.md",
    "ADR-0007-llm-client-wrapper-and-prompt-registry.md",
    "ADR-0008-search-architecture-staged.md",
]


@pytest.mark.parametrize("doc", CANONICAL_DOCS)
def test_canonical_doc_exists(doc: str) -> None:
    p = get_paths().docs / doc
    assert p.exists(), f"Missing canonical doc: {doc}"


@pytest.mark.parametrize("adr", ADRS)
def test_adr_exists(adr: str) -> None:
    p = get_paths().docs / "adr" / adr
    assert p.exists(), f"Missing ADR: {adr}"


def test_index_lists_all_canonical_docs() -> None:
    index_text = (get_paths().docs / "INDEX.md").read_text(encoding="utf-8")
    # Mindestens ein Verweis pro kanonischem Dokument
    for doc in CANONICAL_DOCS:
        if doc == "INDEX.md":  # INDEX.md verweist nicht auf sich selbst
            continue
        assert doc in index_text, f"INDEX.md does not mention {doc}"


def test_roadmap_mentions_all_phases() -> None:
    roadmap = (get_paths().docs / "ROADMAP.md").read_text(encoding="utf-8")
    for phase in ["T0.1", "M1", "M2", "M3", "M4", "M5", "M6", "M7"]:
        assert phase in roadmap, f"ROADMAP.md does not cover phase {phase}"


def test_concepts_present() -> None:
    p = get_paths().docs / "concepts"
    assert (p / "feinkonzept.md").exists()
    assert (p / "methodik_und_lessons_learned.md").exists()
