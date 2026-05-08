"""Tests für ID-Generator."""

from __future__ import annotations

import re

from curiosity_wiki.ids import (
    generate_claim_id,
    generate_job_id,
    generate_page_id,
    generate_proposal_id,
    generate_run_id,
    generate_source_id,
    generate_ulid,
)

CROCKFORD_ALPHABET = re.compile(r"^[0-9A-HJKMNP-TV-Z]+$")


def test_ulid_format() -> None:
    ulid = generate_ulid()
    assert len(ulid) == 26
    assert CROCKFORD_ALPHABET.match(ulid)


def test_ulids_are_unique() -> None:
    ids = {generate_ulid() for _ in range(100)}
    assert len(ids) == 100


def test_source_id_format() -> None:
    sid = generate_source_id()
    assert sid.startswith("src_")
    parts = sid.split("_")
    assert len(parts) == 4
    assert len(parts[1]) == 8  # YYYYMMDD
    assert len(parts[2]) == 6  # HHMMSS
    assert len(parts[3]) == 4  # rand


def test_page_id_format() -> None:
    pid = generate_page_id()
    assert pid.startswith("page_")
    suffix = pid.removeprefix("page_")
    assert len(suffix) == 26


def test_claim_id_format() -> None:
    cid = generate_claim_id()
    assert cid.startswith("clm_")


def test_proposal_id_with_topic() -> None:
    pid = generate_proposal_id("ingest_unesco")
    assert pid.startswith("prop_")
    assert "ingest_unesco" in pid


def test_proposal_id_without_topic_uses_random_suffix() -> None:
    pid = generate_proposal_id()
    assert pid.startswith("prop_")
    parts = pid.split("_")
    assert len(parts[-1]) == 4


def test_proposal_id_sanitises_topic() -> None:
    pid = generate_proposal_id("foo/bar baz!")
    assert "/" not in pid
    assert " " not in pid
    assert "!" not in pid


def test_run_id_format() -> None:
    rid = generate_run_id()
    assert rid.startswith("run_")


def test_job_id_format() -> None:
    jid = generate_job_id()
    assert jid.startswith("job_")
