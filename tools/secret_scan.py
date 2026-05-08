"""Minimal Secret Scan.

T0.1-Stand: regex-basierter Scan über getrackte Dateien. Deckt offensichtliche
Patterns ab (API-Keys, Tokens, Private Keys). Für Produktivbetrieb sollte
zusätzlich gitleaks/trufflehog laufen — das ist später eine eigene Tranche.

Usage::

    python tools/secret_scan.py
    python tools/secret_scan.py --mode tracked   (default)
    python tools/secret_scan.py --mode all
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

# Bewusst eng gefasst — Mojibake der Form "ANTHROPIC_API_KEY=" allein reicht nicht,
# wir wollen wirklich aussehende Secrets erkennen, nicht Variable-Namen.
PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("anthropic-api-key", re.compile(r"sk-ant-[A-Za-z0-9_\-]{20,}")),
    ("openai-api-key", re.compile(r"sk-[A-Za-z0-9]{20,}")),
    ("github-pat", re.compile(r"ghp_[A-Za-z0-9]{36,}")),
    ("github-fine-grained", re.compile(r"github_pat_[A-Za-z0-9_]{50,}")),
    ("aws-access-key", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("private-key-block", re.compile(r"-----BEGIN (RSA|EC|OPENSSH|PRIVATE) KEY-----")),
    (
        "generic-bearer",
        re.compile(r"(?i)bearer\s+[A-Za-z0-9_\-\.=]{30,}"),
    ),
]

# Diese Pfade werden niemals gescannt
EXCLUDE_DIRS = {".git", ".venv", "venv", "node_modules", "__pycache__", ".ruff_cache"}
# Diese Endungen sind binär und werden übersprungen
SKIP_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".pdf", ".zip", ".sqlite", ".db", ".tar"}


@dataclass
class Finding:
    path: str
    line_number: int
    pattern_name: str
    snippet: str


def _list_tracked_files() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return []
    return [REPO_ROOT / line for line in result.stdout.splitlines() if line]


def _list_all_files() -> list[Path]:
    files: list[Path] = []
    for path in REPO_ROOT.rglob("*"):
        if not path.is_file():
            continue
        if any(part in EXCLUDE_DIRS for part in path.parts):
            continue
        files.append(path)
    return files


def _should_skip(path: Path) -> bool:
    if path.suffix.lower() in SKIP_SUFFIXES:
        return True
    # eigene Datei nicht gegen sich selbst scannen
    return path.resolve() == Path(__file__).resolve()


def scan_file(path: Path) -> list[Finding]:
    findings: list[Finding] = []
    if _should_skip(path):
        return findings
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except (OSError, ValueError):
        return findings
    for line_number, line in enumerate(text.splitlines(), start=1):
        for name, pattern in PATTERNS:
            if pattern.search(line):
                findings.append(
                    Finding(
                        path=str(path.relative_to(REPO_ROOT)),
                        line_number=line_number,
                        pattern_name=name,
                        snippet=line.strip()[:120],
                    )
                )
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description="Scan repository for obvious secrets")
    parser.add_argument(
        "--mode",
        choices=["tracked", "all"],
        default="tracked",
        help="tracked = only git-tracked files; all = walk filesystem",
    )
    args = parser.parse_args()

    files = _list_tracked_files() if args.mode == "tracked" else _list_all_files()
    findings: list[Finding] = []
    for f in files:
        findings.extend(scan_file(f))

    if not findings:
        print(f"Secret scan clean ({len(files)} files, mode={args.mode}).")
        return 0

    print(f"Secret scan FAILED ({len(findings)} findings):")
    for finding in findings:
        print(f"  {finding.path}:{finding.line_number} [{finding.pattern_name}] {finding.snippet}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
