"""Run all quality gates and write a summary report.

Stage T0.1: pytest + ruff + secret scan.
Future stages add registry-check, wiki-lint, eval-golden, ui-smoke, ops checks.

Usage::

    python tools/run_quality_gates.py
    python tools/run_quality_gates.py --json
    python tools/run_quality_gates.py --skip-tests   # for fast checks
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


@dataclass
class GateResult:
    name: str
    command: list[str]
    returncode: int
    duration_seconds: float
    stdout_tail: str
    stderr_tail: str

    @property
    def ok(self) -> bool:
        return self.returncode == 0


def _run(name: str, cmd: list[str]) -> GateResult:
    start = time.perf_counter()
    completed = subprocess.run(
        cmd,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    duration = time.perf_counter() - start
    return GateResult(
        name=name,
        command=cmd,
        returncode=completed.returncode,
        duration_seconds=round(duration, 2),
        stdout_tail=completed.stdout[-2000:],
        stderr_tail=completed.stderr[-2000:],
    )


def gate_pytest() -> GateResult:
    return _run("pytest", [sys.executable, "-m", "pytest", "-q"])


def gate_ruff_check() -> GateResult:
    return _run("ruff-check", [sys.executable, "-m", "ruff", "check", "src", "tests", "tools"])


def gate_ruff_format() -> GateResult:
    return _run(
        "ruff-format-check",
        [sys.executable, "-m", "ruff", "format", "--check", "src", "tests", "tools"],
    )


def gate_secret_scan() -> GateResult:
    return _run("secret-scan", [sys.executable, "tools/secret_scan.py"])


def write_report(results: list[GateResult]) -> Path:
    timestamp = datetime.now(tz=UTC).strftime("%Y%m%d-%H%M%S")
    out_dir = REPO_ROOT / "docs" / "_ops" / "quality_gates" / timestamp
    out_dir.mkdir(parents=True, exist_ok=True)
    summary_path = out_dir / "summary.md"

    overall_ok = all(r.ok for r in results)
    lines = [
        f"# Quality Gates — {timestamp}",
        "",
        f"**Status:** {'PASS' if overall_ok else 'FAIL'}",
        "",
        "| Gate | Result | Duration |",
        "|---|---|---:|",
    ]
    for r in results:
        status = "PASS" if r.ok else "FAIL"
        lines.append(f"| {r.name} | {status} | {r.duration_seconds}s |")
    lines.append("")
    for r in results:
        lines.append(f"## {r.name}")
        lines.append("")
        lines.append(f"Command: `{' '.join(r.command)}`")
        lines.append("")
        if r.stdout_tail:
            lines.append("```")
            lines.append(r.stdout_tail.rstrip())
            lines.append("```")
            lines.append("")
        if r.stderr_tail:
            lines.append("**stderr:**")
            lines.append("")
            lines.append("```")
            lines.append(r.stderr_tail.rstrip())
            lines.append("```")
            lines.append("")
    summary_path.write_text("\n".join(lines), encoding="utf-8")
    return summary_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Run all quality gates")
    parser.add_argument("--json", action="store_true", help="Emit JSON summary on stdout")
    parser.add_argument("--skip-tests", action="store_true", help="Skip pytest (fast mode)")
    args = parser.parse_args()

    gates = [gate_ruff_check, gate_ruff_format, gate_secret_scan]
    if not args.skip_tests:
        gates.insert(0, gate_pytest)

    results = [g() for g in gates]
    summary_path = write_report(results)

    if args.json:
        print(json.dumps([asdict(r) for r in results], indent=2))
    else:
        for r in results:
            mark = "OK  " if r.ok else "FAIL"
            print(f"[{mark}] {r.name:20s} ({r.duration_seconds:5.2f}s)")
        print(f"\nSummary written to: {summary_path.relative_to(REPO_ROOT)}")

    return 0 if all(r.ok for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
