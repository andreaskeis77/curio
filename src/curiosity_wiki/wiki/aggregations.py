"""Open-Questions und Freshness-Dashboard-Daten (M4).

Beide Aggregationen werden aus der Registry und/oder den Wiki-Markdown-Files gebaut.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from pathlib import Path

from curiosity_wiki.paths import VaultPaths, get_paths
from curiosity_wiki.wiki.frontmatter import FrontmatterError, parse_frontmatter
from curiosity_wiki.wiki.models import PageType


@dataclass
class OpenQuestion:
    """Eine offene Frage aus dem Wiki."""

    text: str
    page_id: str | None
    page_title: str
    page_path: str
    source: str  # 'question_page' | 'frontmatter'


@dataclass
class FreshnessEntry:
    """Eine Page mit Freshness-Status fuer das Dashboard."""

    page_id: str
    title: str
    page_type: str
    relative_path: str
    freshness: str
    review_after: date | None
    days_overdue: int | None  # negativ = noch nicht faellig, 0 = heute, >0 = ueberfaellig


@dataclass
class FreshnessReport:
    """Aggregierter Freshness-Status."""

    overdue: list[FreshnessEntry] = field(default_factory=list)
    due_within_7_days: list[FreshnessEntry] = field(default_factory=list)
    volatile_without_schedule: list[FreshnessEntry] = field(default_factory=list)


def _walk_wiki_files(wiki_root: Path) -> list[Path]:
    if not wiki_root.exists():
        return []
    return [
        path
        for path in wiki_root.rglob("*.md")
        if not any(part.startswith("_") or part == "README.md" for part in path.parts)
    ]


def collect_open_questions(
    paths: VaultPaths | None = None,
) -> list[OpenQuestion]:
    """Aggregiert Open-Questions aus Wiki-Pages.

    Quellen:
    - Frontmatter ``open_questions``-Liste auf jeder Page.
    - Pages vom Typ ``question`` (komplette Page steht fuer eine Frage).
    """
    paths = paths or get_paths()
    out: list[OpenQuestion] = []
    for path in _walk_wiki_files(paths.wiki):
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        try:
            front, _ = parse_frontmatter(text)
        except FrontmatterError:
            continue
        page_id = front.data.get("id")
        page_title = str(front.data.get("title") or "")
        page_type = str(front.data.get("type") or "")
        rel = str(path.relative_to(paths.root)) if paths.root in path.parents else str(path)
        if page_type == PageType.QUESTION.value:
            out.append(
                OpenQuestion(
                    text=page_title,
                    page_id=str(page_id) if page_id else None,
                    page_title=page_title,
                    page_path=rel,
                    source="question_page",
                )
            )
        for q in front.data.get("open_questions") or []:
            text_q = str(q).strip()
            if not text_q:
                continue
            out.append(
                OpenQuestion(
                    text=text_q,
                    page_id=str(page_id) if page_id else None,
                    page_title=page_title,
                    page_path=rel,
                    source="frontmatter",
                )
            )
    return out


def _coerce_review_date(value: object) -> date | None:
    if value is None:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    text = str(value).split("T")[0]
    try:
        return date.fromisoformat(text)
    except (TypeError, ValueError):
        return None


def collect_freshness_status(
    conn: sqlite3.Connection,
    *,
    today: date | None = None,
) -> FreshnessReport:
    """Liefert Pages, deren Freshness Aufmerksamkeit braucht.

    Drei Buckets:

    - ``overdue``: ``review_after < today``.
    - ``due_within_7_days``: ``today <= review_after <= today + 7``.
    - ``volatile_without_schedule``: ``freshness=volatile`` und ``review_after IS NULL``.
    """
    today = today or datetime.now(tz=UTC).date()
    rows = conn.execute(
        """
        SELECT id, title, type, path, freshness, review_after
        FROM pages
        WHERE status = 'active'
        """
    ).fetchall()
    report = FreshnessReport()
    for row in rows:
        review_after = _coerce_review_date(row["review_after"])
        page_type = str(row["type"])
        freshness = str(row["freshness"] or "")
        entry = FreshnessEntry(
            page_id=str(row["id"]),
            title=str(row["title"]),
            page_type=page_type,
            relative_path=str(row["path"]),
            freshness=freshness,
            review_after=review_after,
            days_overdue=(today - review_after).days if review_after else None,
        )
        if review_after and review_after < today:
            report.overdue.append(entry)
        elif review_after and (review_after - today).days <= 7:
            report.due_within_7_days.append(entry)
        if freshness == "volatile" and review_after is None:
            report.volatile_without_schedule.append(entry)
    return report
