"""Lightweight task runner.

Dünner Wrapper um häufige Befehle. Existiert, damit das ENGINEERING_MANIFEST
und der RUNBOOK auf einen einzigen Einstiegspunkt zeigen können.

Usage::

    python tools/task_runner.py test
    python tools/task_runner.py lint
    python tools/task_runner.py format
    python tools/task_runner.py format-check
    python tools/task_runner.py quality-gates
    python tools/task_runner.py secret-scan
    python tools/task_runner.py info
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

TASKS: dict[str, list[str]] = {
    "test": [sys.executable, "-m", "pytest", "-q"],
    "lint": [sys.executable, "-m", "ruff", "check", "src", "tests", "tools"],
    "format-check": [
        sys.executable,
        "-m",
        "ruff",
        "format",
        "--check",
        "src",
        "tests",
        "tools",
    ],
    "format": [sys.executable, "-m", "ruff", "format", "src", "tests", "tools"],
    "secret-scan": [sys.executable, "tools/secret_scan.py"],
    "quality-gates": [sys.executable, "tools/run_quality_gates.py"],
    "info": [sys.executable, "-m", "curiosity_wiki", "info"],
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Curiosity task runner")
    parser.add_argument("task", choices=sorted(TASKS.keys()))
    args = parser.parse_args()
    cmd = TASKS[args.task]
    completed = subprocess.run(cmd, cwd=REPO_ROOT, check=False)
    return completed.returncode


if __name__ == "__main__":
    sys.exit(main())
