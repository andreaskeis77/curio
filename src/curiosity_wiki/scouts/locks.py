"""PID-File-Lock fuer Scout-Runs (M7, ADR-0019)."""

from __future__ import annotations

import json
import os
import socket
from datetime import UTC, datetime, timedelta
from pathlib import Path

STALE_THRESHOLD = timedelta(hours=1)


class LockBusyError(RuntimeError):
    """Lock wird gerade von einem anderen Prozess gehalten."""


def _lock_payload() -> dict[str, str | int]:
    return {
        "pid": os.getpid(),
        "started_at": datetime.now(tz=UTC).isoformat(timespec="seconds"),
        "host": socket.gethostname(),
    }


def _is_pid_alive(pid: int) -> bool:
    """Plattform-tolerantes ``kill(pid, 0)``-Aequivalent."""
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def _is_stale(payload: dict, *, now: datetime | None = None) -> bool:
    now = now or datetime.now(tz=UTC)
    started_raw = str(payload.get("started_at") or "")
    try:
        started = datetime.fromisoformat(started_raw)
    except ValueError:
        return True
    if started.tzinfo is None:
        started = started.replace(tzinfo=UTC)
    age = now - started
    if age > STALE_THRESHOLD:
        return True
    pid = int(payload.get("pid") or 0)
    return bool(pid > 0 and not _is_pid_alive(pid))


def acquire_lock(lock_path: Path, *, force: bool = False) -> None:
    """Erstellt das Lock-File. Stale-Locks werden uebernommen, ausser ``force=False``.

    ``force=True`` umgeht die Staleness-Heuristik (Notfall-Cleanup).
    """
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    if lock_path.exists():
        try:
            existing = json.loads(lock_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            existing = {}
        if not (force or _is_stale(existing)):
            raise LockBusyError(
                f"Scout lock held by pid={existing.get('pid')} "
                f"on {existing.get('host')}, started={existing.get('started_at')}"
            )
        # stale oder force: alten Lock entfernen.
        try:
            lock_path.unlink()
        except OSError as exc:
            raise LockBusyError(f"could not remove stale lock {lock_path}: {exc}") from exc
    payload = _lock_payload()
    # Atomic-create: O_CREAT|O_EXCL
    fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    try:
        os.write(fd, json.dumps(payload).encode("utf-8"))
    finally:
        os.close(fd)


def release_lock(lock_path: Path) -> None:
    """Entfernt das Lock-File (best effort)."""
    try:
        if lock_path.exists():
            lock_path.unlink()
    except OSError:
        pass
