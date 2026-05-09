"""Golden-Questions-Runner (M4).

Liest ``eval/golden-questions.yaml`` und prueft jede Frage gegen die aktuellen
Search-/Browse-/Aggregation-Funktionen. Liefert ein strukturiertes Ergebnis,
das die CLI als Tabelle und Markdown-Report rendert.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from curiosity_wiki.browse import (
    browse_by_collection,
    browse_by_topic,
    browse_random,
)
from curiosity_wiki.paths import VaultPaths, get_paths
from curiosity_wiki.search import (
    SearchError,
    rebuild_index_from_markdown,
    search_pages,
)
from curiosity_wiki.wiki.aggregations import (
    collect_freshness_status,
    collect_open_questions,
)


@dataclass
class GoldenResult:
    """Ergebnis pro Frage."""

    id: str
    description: str
    type: str
    passed: bool
    detail: str = ""


@dataclass
class GoldenRun:
    """Aggregation aller Frage-Ergebnisse."""

    results: list[GoldenResult] = field(default_factory=list)

    @property
    def passed(self) -> int:
        return sum(1 for r in self.results if r.passed)

    @property
    def failed(self) -> int:
        return sum(1 for r in self.results if not r.passed)

    @property
    def total(self) -> int:
        return len(self.results)


def _load_questions(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"Golden questions file not found: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or []
    if not isinstance(data, list):
        raise ValueError(f"Golden questions file must be a list, got {type(data).__name__}")
    return [item for item in data if isinstance(item, dict)]


def _check_count(
    n: int,
    expectations: dict[str, Any],
) -> tuple[bool, str]:
    detail_parts: list[str] = [f"hits={n}"]
    min_hits = expectations.get("min_hits")
    max_hits = expectations.get("max_hits")
    allow_empty = bool(expectations.get("allow_empty", True))
    if not allow_empty and n == 0:
        return False, f"empty result (allow_empty=false), hits={n}"
    if min_hits is not None and n < int(min_hits):
        return False, f"hits={n} < min_hits={min_hits}"
    if max_hits is not None and n > int(max_hits):
        return False, f"hits={n} > max_hits={max_hits}"
    return True, ", ".join(detail_parts)


def _eval_question(
    question: dict[str, Any],
    *,
    conn: sqlite3.Connection,
    paths: VaultPaths,
) -> GoldenResult:
    qid = str(question.get("id") or "?")
    qtype = str(question.get("type") or "")
    description = str(question.get("description") or "")
    expectations = dict(question.get("expectations") or {})
    expect_error = expectations.get("expect_error")

    def _ok(detail: str) -> GoldenResult:
        return GoldenResult(id=qid, description=description, type=qtype, passed=True, detail=detail)

    def _fail(detail: str) -> GoldenResult:
        return GoldenResult(
            id=qid, description=description, type=qtype, passed=False, detail=detail
        )

    try:
        if qtype == "search":
            filters = dict(question.get("filters") or {})
            hits = search_pages(
                conn,
                str(question.get("query") or ""),
                page_type=filters.get("type"),
                freshness=filters.get("freshness"),
                status=filters.get("status"),
                tag=filters.get("tag"),
                limit=int(question.get("limit", 20)),
            )
            ok, detail = _check_count(len(hits), expectations)
            return _ok(detail) if ok else _fail(detail)
        if qtype == "browse_random":
            hits = browse_random(conn, limit=int(question.get("limit", 5)))
            ok, detail = _check_count(len(hits), expectations)
            return _ok(detail) if ok else _fail(detail)
        if qtype == "browse_topic":
            hits = browse_by_topic(
                conn, str(question.get("topic") or ""), limit=int(question.get("limit", 50))
            )
            ok, detail = _check_count(len(hits), expectations)
            return _ok(detail) if ok else _fail(detail)
        if qtype == "browse_collection":
            hits = browse_by_collection(
                conn, str(question.get("collection") or ""), limit=int(question.get("limit", 50))
            )
            ok, detail = _check_count(len(hits), expectations)
            return _ok(detail) if ok else _fail(detail)
        if qtype == "open_questions":
            items = collect_open_questions(paths)
            ok, detail = _check_count(len(items), expectations)
            return _ok(detail) if ok else _fail(detail)
        if qtype == "freshness":
            report = collect_freshness_status(conn)
            n = (
                len(report.overdue)
                + len(report.due_within_7_days)
                + len(report.volatile_without_schedule)
            )
            ok, detail = _check_count(n, expectations)
            return _ok(detail or f"buckets summed to {n}") if ok else _fail(detail)
        if qtype == "index_rebuild":
            result = rebuild_index_from_markdown(conn, paths=paths)
            min_files = expectations.get("min_files_scanned")
            if min_files is not None and result.files_scanned < int(min_files):
                return _fail(f"files_scanned={result.files_scanned} < min={min_files}")
            return _ok(f"files_scanned={result.files_scanned}, rows_written={result.rows_written}")
        return _fail(f"unknown question type: {qtype!r}")
    except SearchError as exc:
        if expect_error == "SearchError":
            return _ok(f"expected SearchError raised: {exc}")
        return _fail(f"unexpected SearchError: {exc}")
    except Exception as exc:
        if expect_error and exc.__class__.__name__ == expect_error:
            return _ok(f"expected {expect_error}: {exc}")
        return _fail(f"{exc.__class__.__name__}: {exc}")


def run_golden_questions(
    conn: sqlite3.Connection,
    *,
    paths: VaultPaths | None = None,
    questions_file: Path | None = None,
) -> GoldenRun:
    """Fuehrt alle Goldens aus und liefert das aggregierte Ergebnis."""
    paths = paths or get_paths()
    questions_file = questions_file or (paths.root / "eval" / "golden-questions.yaml")
    questions = _load_questions(questions_file)
    run = GoldenRun()
    for question in questions:
        run.results.append(_eval_question(question, conn=conn, paths=paths))
    return run


def write_golden_report(run: GoldenRun, target_path: Path) -> None:
    """Markdown-Report nach ``docs/_ops/eval_reports/<run>.md``."""
    lines = [
        "# Golden Questions Report",
        "",
        f"**Total:** {run.total}  **Passed:** {run.passed}  **Failed:** {run.failed}",
        "",
    ]
    for result in run.results:
        status = "PASS" if result.passed else "FAIL"
        lines.append(f"## {result.id} [{status}]")
        lines.append("")
        lines.append(f"- **Type:** {result.type}")
        lines.append(f"- **Description:** {result.description}")
        if result.detail:
            lines.append(f"- **Detail:** {result.detail}")
        lines.append("")
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text("\n".join(lines), encoding="utf-8")
