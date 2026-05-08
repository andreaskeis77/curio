"""Tests für Hashing-Utilities."""

from __future__ import annotations

from pathlib import Path

from curiosity_wiki.sources.hashing import hash_bytes, hash_file


def test_hash_bytes_known_value() -> None:
    # Standard SHA-256 of b"hello"
    assert (
        hash_bytes(b"hello") == "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"
    )


def test_hash_bytes_empty() -> None:
    assert hash_bytes(b"") == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"


def test_hash_file_matches_hash_bytes(tmp_path: Path) -> None:
    payload = b"curiosity wiki test content\n"
    target = tmp_path / "sample.bin"
    target.write_bytes(payload)
    assert hash_file(target) == hash_bytes(payload)


def test_hash_file_large_chunked(tmp_path: Path) -> None:
    payload = b"a" * (200 * 1024)  # > one chunk
    target = tmp_path / "large.bin"
    target.write_bytes(payload)
    assert hash_file(target) == hash_bytes(payload)
