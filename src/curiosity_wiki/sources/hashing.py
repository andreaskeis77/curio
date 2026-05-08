"""SHA-256-Hashing über Dateien und Bytes."""

from __future__ import annotations

import hashlib
from pathlib import Path

CHUNK_SIZE = 64 * 1024  # 64 KiB


def hash_bytes(data: bytes) -> str:
    """SHA-256 als Hex-String."""
    return hashlib.sha256(data).hexdigest()


def hash_file(path: Path) -> str:
    """SHA-256 einer Datei. Liest in 64-KiB-Chunks, um RAM zu schonen."""
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            chunk = fh.read(CHUNK_SIZE)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()
