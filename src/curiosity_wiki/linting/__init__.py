"""curiosity_wiki.linting — Wiki-Quality-Gates (M3).

Public API:

- ``LintFinding`` — strukturiertes Finding mit Severity und Type.
- ``LintReport`` — Aggregat eines Lint-Laufs.
- ``run_lint(conn, paths)`` — Top-Level: scannt Wiki und Registry.
"""

from __future__ import annotations

from curiosity_wiki.linting.lint import (
    LintFinding,
    LintReport,
    LintSeverity,
    run_lint,
    write_report_markdown,
)

__all__ = [
    "LintFinding",
    "LintReport",
    "LintSeverity",
    "run_lint",
    "write_report_markdown",
]
