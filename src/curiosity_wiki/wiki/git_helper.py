"""Schmale Git-Helpers fuer Auto-Commit nach Approval (ADR-0012)."""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path


class GitHelperError(RuntimeError):
    """Wird geworfen, wenn ein Git-Befehl fehlschlaegt."""


@dataclass(frozen=True)
class GitStatusResult:
    """Output von ``git status --porcelain`` als strukturierte Daten."""

    has_uncommitted_changes: bool
    files_changed: list[str]
    in_repo: bool


def is_git_repo(repo_root: Path) -> bool:
    return (repo_root / ".git").exists()


def git_status(repo_root: Path) -> GitStatusResult:
    """``git status --porcelain`` auswerten."""
    if not is_git_repo(repo_root):
        return GitStatusResult(has_uncommitted_changes=False, files_changed=[], in_repo=False)
    completed = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise GitHelperError(f"git status failed: {completed.stderr.strip()}")
    files: list[str] = []
    for line in completed.stdout.splitlines():
        # Format: "XY filename"
        if len(line) > 3:
            files.append(line[3:])
    return GitStatusResult(
        has_uncommitted_changes=bool(files),
        files_changed=files,
        in_repo=True,
    )


def git_add_files(repo_root: Path, paths: list[str]) -> None:
    if not paths:
        return
    completed = subprocess.run(
        ["git", "add", "--", *paths],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise GitHelperError(f"git add failed: {completed.stderr.strip()}")


def git_commit(repo_root: Path, message: str) -> str:
    """Erzeugt einen Commit. Liefert den Commit-Hash."""
    env = os.environ.copy()
    completed = subprocess.run(
        ["git", "commit", "-m", message],
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise GitHelperError(
            f"git commit failed: {completed.stderr.strip() or completed.stdout.strip()}"
        )
    rev = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    return rev.stdout.strip() if rev.returncode == 0 else ""


def auto_commit_publish(
    *,
    repo_root: Path,
    relative_paths: list[str],
    message: str,
    require_clean_other_changes: bool = True,
) -> str | None:
    """Stage + commit nur die genannten Pfade.

    Wenn ``require_clean_other_changes=True`` und es gibt andere uncommitted
    Aenderungen ausserhalb der Publish-Pfade, wird **nicht** committed
    und ``None`` zurueckgegeben (Andreas committet manuell).

    Liefert den Commit-Hash bei Erfolg, sonst ``None``.
    """
    status = git_status(repo_root)
    if not status.in_repo:
        return None
    if require_clean_other_changes:
        publish_set = set(_normalize_path(p) for p in relative_paths)
        other = [p for p in status.files_changed if _normalize_path(p) not in publish_set]
        if other:
            return None
    git_add_files(repo_root, relative_paths)
    return git_commit(repo_root, message)


def _normalize_path(p: str) -> str:
    """Linux- und Windows-Slashes vereinheitlichen."""
    return p.replace("\\", "/")
