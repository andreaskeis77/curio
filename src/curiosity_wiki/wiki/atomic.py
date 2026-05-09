"""Atomic-Write-Helpers (ADR-0012)."""

from __future__ import annotations

import contextlib
import os
from pathlib import Path


def atomic_write_text(path: Path, content: str, *, encoding: str = "utf-8") -> None:
    """Schreibt ``content`` atomar nach ``path``.

    Reihenfolge: temp file -> fsync -> atomic rename. Bei Fehler bleibt
    die alte Datei unangetastet und die temp file wird (best effort) entfernt.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    try:
        with tmp.open("w", encoding=encoding, newline="\n") as fh:
            fh.write(content)
            fh.flush()
            # fsync ist auf Windows-Files manchmal limitiert; nicht fatal.
            with contextlib.suppress(OSError, AttributeError):
                os.fsync(fh.fileno())
        tmp.replace(path)
    except Exception:
        # Cleanup, dann re-raise
        with contextlib.suppress(OSError):
            if tmp.exists():
                tmp.unlink()
        raise
