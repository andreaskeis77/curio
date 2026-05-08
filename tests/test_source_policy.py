"""Tests für die Source-Policy-Heuristik."""

from __future__ import annotations

from curiosity_wiki.sources.models import (
    AccessType,
    CopyrightRisk,
    Reliability,
)
from curiosity_wiki.sources.policy import guess_source_policy


def test_no_url_returns_own_note_default() -> None:
    p = guess_source_policy(None)
    assert p.access == AccessType.OWN_NOTE
    assert p.reliability == Reliability.PERSONAL


def test_unesco_is_official_low_risk() -> None:
    p = guess_source_policy("https://whc.unesco.org/en/list/314")
    assert p.reliability == Reliability.OFFICIAL
    assert p.copyright_risk == CopyrightRisk.LOW


def test_wikipedia_is_journalistic_medium_risk() -> None:
    p = guess_source_policy("https://de.wikipedia.org/wiki/Alhambra")
    assert p.reliability == Reliability.JOURNALISTIC
    assert p.copyright_risk == CopyrightRisk.MEDIUM


def test_paywall_blocks_llm() -> None:
    p = guess_source_policy("https://www.spiegel.de/some-article")
    assert p.access == AccessType.PAYWALLED
    assert p.copyright_risk == CopyrightRisk.HIGH
    assert p.llm_allowed is False


def test_unknown_domain_default_public_medium() -> None:
    p = guess_source_policy("https://random-blog-12345.example.com/post")
    assert p.access == AccessType.PUBLIC
    assert p.reliability == Reliability.UNKNOWN
    assert p.copyright_risk == CopyrightRisk.MEDIUM


def test_subdomain_matches_official() -> None:
    p = guess_source_policy("https://api.europa.eu/something")
    assert p.reliability == Reliability.OFFICIAL


def test_arxiv_is_expert() -> None:
    p = guess_source_policy("https://arxiv.org/abs/2401.12345")
    assert p.reliability == Reliability.EXPERT
