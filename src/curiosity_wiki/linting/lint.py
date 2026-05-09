"""Wiki-Lint (M3 Basisregeln + M4 Erweiterungen).

Regeln (Severity in Klammern):

1. **frontmatter_invalid** (error): Pflichtfelder fehlen oder Enum-Werte ungueltig.
2. **slug_mismatch** (warning): Frontmatter-Slug != Datei-Pfad.
3. **claim_missing_source** (warning): Heuristik findet harten Fakt ohne Quellen-Beleg.
   Wikilink-Inhalte (``[[...]]``) werden vor dem Pattern-Match entfernt, um false
   positives wie ``[[Pacojet 1984]]`` zu vermeiden.
4. **page_without_sources** (warning): Page-Frontmatter hat leere ``sources``-Liste.
5. **broken_wikilink** (warning): ``[[Title]]`` zeigt auf nicht-existente Page.
6. **duplicate_title** (warning): Mehrere Pages mit identischem Titel.
7. **product_without_review_after** (error): Produkt-Seite ohne ``review_after``.
8. **review_after_overdue** (warning): ``review_after`` in der Vergangenheit.
9. **page_too_long** (warning): Body > 2500 Woerter.
10. **stale_extracted_path** (info): ``extracted_path`` in DB zeigt auf nicht existente Datei.
11. **volatile_without_review_after** (warning): Freshness ``volatile`` ohne ``review_after``.
12. **orphan_page** (info): Page ohne Backlinks (M4). Source-, Question- und
    Collection-Pages sind ausgenommen.
13. **alias_collision** (warning): Alias eines Pages ist Title eines anderen Pages (M4).
"""

from __future__ import annotations

import re
import sqlite3
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from enum import StrEnum
from pathlib import Path

from curiosity_wiki.ids import generate_run_id
from curiosity_wiki.paths import VaultPaths, get_paths
from curiosity_wiki.wiki.frontmatter import (
    FrontmatterError,
    parse_frontmatter,
    validate_frontmatter,
)
from curiosity_wiki.wiki.models import PageType
from curiosity_wiki.wiki.repository import LinkRepository, PageRepository


class LintSeverity(StrEnum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass(frozen=True)
class LintFinding:
    severity: LintSeverity
    finding_type: str
    file_path: str | None
    page_id: str | None
    source_id: str | None
    message: str


@dataclass
class LintReport:
    run_id: str
    started_at: datetime
    finished_at: datetime
    findings: list[LintFinding] = field(default_factory=list)

    @property
    def errors(self) -> int:
        return sum(1 for f in self.findings if f.severity == LintSeverity.ERROR)

    @property
    def warnings(self) -> int:
        return sum(1 for f in self.findings if f.severity == LintSeverity.WARNING)

    @property
    def infos(self) -> int:
        return sum(1 for f in self.findings if f.severity == LintSeverity.INFO)


# Heuristik fuer „harte Fakten" (siehe ADR-0013)
HARD_FACT_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("year", re.compile(r"\b(?:18|19|20)\d{2}\b")),
    ("price", re.compile(r"\b\d+(?:[.,]\d+)?\s?(?:€|EUR|USD|\$)\b", re.IGNORECASE)),
    ("percent", re.compile(r"\b\d+(?:[.,]\d+)?\s?%")),
    ("quote", re.compile(r"[„\"']{1,2}.{30,}[„\"']{1,2}")),
]

# Wikilink-Pattern fuers Strippen vor Hard-Fact-Heuristik.
WIKILINK_RE = re.compile(r"\[\[[^\]]+?\]\]")


def _walk_wiki_files(wiki_root: Path) -> list[Path]:
    """Alle .md-Dateien unter ``wiki/``, ohne ``_meta/``."""
    if not wiki_root.exists():
        return []
    out: list[Path] = []
    for path in wiki_root.rglob("*.md"):
        if any(part.startswith("_") or part == "README.md" for part in path.parts):
            continue
        out.append(path)
    return out


def _check_frontmatter(path: Path) -> tuple[dict | None, list[LintFinding]]:
    findings: list[LintFinding] = []
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        findings.append(
            LintFinding(
                severity=LintSeverity.ERROR,
                finding_type="file_unreadable",
                file_path=str(path),
                page_id=None,
                source_id=None,
                message=str(exc),
            )
        )
        return None, findings
    try:
        front, _ = parse_frontmatter(text)
    except FrontmatterError as exc:
        findings.append(
            LintFinding(
                severity=LintSeverity.ERROR,
                finding_type="frontmatter_invalid",
                file_path=str(path),
                page_id=None,
                source_id=None,
                message=str(exc),
            )
        )
        return None, findings
    errors = validate_frontmatter(front)
    if errors:
        findings.append(
            LintFinding(
                severity=LintSeverity.ERROR,
                finding_type="frontmatter_invalid",
                file_path=str(path),
                page_id=str(front.data.get("id") or ""),
                source_id=None,
                message="; ".join(errors),
            )
        )
        return front.data, findings
    return front.data, findings


def _check_slug_path(path: Path, data: dict, vault_root: Path) -> list[LintFinding]:
    findings: list[LintFinding] = []
    expected_slug = str(data.get("slug", ""))
    actual_stem = path.stem
    if expected_slug and actual_stem and expected_slug != actual_stem:
        findings.append(
            LintFinding(
                severity=LintSeverity.WARNING,
                finding_type="slug_mismatch",
                file_path=str(path.relative_to(vault_root)),
                page_id=str(data.get("id") or ""),
                source_id=None,
                message=f"frontmatter slug '{expected_slug}' != filename '{actual_stem}'",
            )
        )
    return findings


def _check_sources(path: Path, data: dict, vault_root: Path) -> list[LintFinding]:
    sources = data.get("sources") or []
    page_type = str(data.get("type", ""))
    findings: list[LintFinding] = []
    if page_type == PageType.SOURCE.value:
        return findings
    if not sources:
        findings.append(
            LintFinding(
                severity=LintSeverity.WARNING,
                finding_type="page_without_sources",
                file_path=str(path.relative_to(vault_root)),
                page_id=str(data.get("id") or ""),
                source_id=None,
                message="Page has no sources in frontmatter",
            )
        )
    return findings


def _check_hard_facts(path: Path, body: str, data: dict, vault_root: Path) -> list[LintFinding]:
    """Wenn Heuristik harten Fakt findet, der nicht in einem Claim-Marker steht."""
    findings: list[LintFinding] = []
    page_type = str(data.get("type", ""))
    if page_type == PageType.SOURCE.value:
        return findings
    # Belegbare Fakten = Body-Zeilen, die einen Claim-Marker enthalten
    claim_lines = {
        i for i, line in enumerate(body.splitlines()) if "claim:" in line and "source:" in line
    }
    for fact_type, pattern in HARD_FACT_PATTERNS:
        for line_no, line in enumerate(body.splitlines()):
            if line.lstrip().startswith("#"):
                continue
            if "claim:" in line:
                continue
            # Wikilink-Inhalte ausblenden, damit z.B. ``[[Pacojet 1984]]`` nicht
            # als Year-Fakt zaehlt. Der Linktext steht meist im Ziel-Page selbst.
            scan_line = WIKILINK_RE.sub("", line)
            if pattern.search(scan_line):
                # gibt es im selben Listen-Block (naechste 3 Zeilen) einen Claim-Marker?
                if any(line_no + offset in claim_lines for offset in range(1, 4)):
                    continue
                findings.append(
                    LintFinding(
                        severity=LintSeverity.WARNING,
                        finding_type="claim_missing_source",
                        file_path=str(path.relative_to(vault_root)),
                        page_id=str(data.get("id") or ""),
                        source_id=None,
                        message=(
                            f"hard fact ({fact_type}) without claim-marker on line {line_no + 1}: "
                            f"{line.strip()[:80]}"
                        ),
                    )
                )
                break  # pro Pattern nur ein Finding pro Page
    return findings


def _check_volatile(path: Path, data: dict, vault_root: Path) -> list[LintFinding]:
    findings: list[LintFinding] = []
    page_type = str(data.get("type", ""))
    freshness = str(data.get("freshness", ""))
    review_after = data.get("review_after")
    today = date.today()
    if page_type == PageType.PRODUCT_RESEARCH.value and review_after is None:
        findings.append(
            LintFinding(
                severity=LintSeverity.ERROR,
                finding_type="product_without_review_after",
                file_path=str(path.relative_to(vault_root)),
                page_id=str(data.get("id") or ""),
                source_id=None,
                message="Product page must have a review_after date",
            )
        )
    if review_after:
        try:
            if isinstance(review_after, date):
                ra = review_after
            else:
                ra = date.fromisoformat(str(review_after).split("T")[0])
            if ra < today:
                findings.append(
                    LintFinding(
                        severity=LintSeverity.WARNING,
                        finding_type="review_after_overdue",
                        file_path=str(path.relative_to(vault_root)),
                        page_id=str(data.get("id") or ""),
                        source_id=None,
                        message=f"review_after {ra.isoformat()} is overdue (today {today.isoformat()})",
                    )
                )
        except (ValueError, TypeError):
            pass
    if freshness == "volatile" and review_after is None:
        findings.append(
            LintFinding(
                severity=LintSeverity.WARNING,
                finding_type="volatile_without_review_after",
                file_path=str(path.relative_to(vault_root)),
                page_id=str(data.get("id") or ""),
                source_id=None,
                message="volatile freshness should have a review_after date",
            )
        )
    return findings


def _check_length(path: Path, body: str, data: dict, vault_root: Path) -> list[LintFinding]:
    word_count = len(body.split())
    if word_count > 2500:
        return [
            LintFinding(
                severity=LintSeverity.WARNING,
                finding_type="page_too_long",
                file_path=str(path.relative_to(vault_root)),
                page_id=str(data.get("id") or ""),
                source_id=None,
                message=f"page has {word_count} words; consider splitting (limit 2500)",
            )
        ]
    return []


def _check_duplicate_titles(
    page_data: list[tuple[Path, dict]], vault_root: Path
) -> list[LintFinding]:
    by_title: dict[str, list[Path]] = defaultdict(list)
    for path, data in page_data:
        title = str(data.get("title", "")).strip().lower()
        if title:
            by_title[title].append(path)
    findings: list[LintFinding] = []
    for title, paths in by_title.items():
        if len(paths) > 1:
            for path in paths:
                findings.append(
                    LintFinding(
                        severity=LintSeverity.WARNING,
                        finding_type="duplicate_title",
                        file_path=str(path.relative_to(vault_root)),
                        page_id=None,
                        source_id=None,
                        message=f"title '{title}' shared with {len(paths) - 1} other page(s)",
                    )
                )
    return findings


def _check_wikilinks(
    page_data: list[tuple[Path, dict, str]], vault_root: Path
) -> list[LintFinding]:
    """Findet ``[[Title]]`` und prueft, ob ein Page-Title oder Alias matcht."""
    titles: set[str] = set()
    for _, data, _ in page_data:
        if data.get("title"):
            titles.add(str(data["title"]).strip().lower())
        for alias in data.get("aliases") or []:
            titles.add(str(alias).strip().lower())
    findings: list[LintFinding] = []
    pattern = re.compile(r"\[\[([^\]]+?)\]\]")
    for path, data, body in page_data:
        for match in pattern.finditer(body):
            target = match.group(1).split("|")[0].strip().lower()
            if target not in titles:
                findings.append(
                    LintFinding(
                        severity=LintSeverity.WARNING,
                        finding_type="broken_wikilink",
                        file_path=str(path.relative_to(vault_root)),
                        page_id=str(data.get("id") or ""),
                        source_id=None,
                        message=f"wikilink to unknown page: [[{match.group(1)}]]",
                    )
                )
    return findings


# Orphan-Page-Whitelist: Page-Types, die strukturell ohne Backlinks sinnvoll sind.
ORPHAN_EXEMPT_TYPES = {
    PageType.SOURCE.value,
    PageType.QUESTION.value,
    PageType.COLLECTION.value,
}


def _check_orphan_pages(conn: sqlite3.Connection) -> list[LintFinding]:
    """Page in DB ohne eingehende Backlinks (links.to_page_id), ausser whitelisted Types."""
    findings: list[LintFinding] = []
    page_repo = PageRepository(conn)
    link_repo = LinkRepository(conn)
    for page in page_repo.list_all(limit=10000):
        if page.page_type.value in ORPHAN_EXEMPT_TYPES:
            continue
        if link_repo.backlinks(page.id):
            continue
        findings.append(
            LintFinding(
                severity=LintSeverity.INFO,
                finding_type="orphan_page",
                file_path=page.relative_path,
                page_id=page.id,
                source_id=None,
                message=(
                    f"page '{page.title}' (type={page.page_type.value}) has no incoming "
                    "wikilinks; consider linking it from a topic, collection, or related page"
                ),
            )
        )
    return findings


def _check_alias_collisions(
    page_data: list[tuple[Path, dict]], vault_root: Path
) -> list[LintFinding]:
    """Alias eines Pages = Title eines anderen Pages (case-insensitive)."""
    titles_by_path: dict[str, Path] = {}
    for path, data in page_data:
        title = str(data.get("title", "")).strip().lower()
        if title:
            titles_by_path[title] = path
    findings: list[LintFinding] = []
    for path, data in page_data:
        own_title = str(data.get("title", "")).strip().lower()
        for alias in data.get("aliases") or []:
            alias_norm = str(alias).strip().lower()
            if not alias_norm or alias_norm == own_title:
                continue
            other = titles_by_path.get(alias_norm)
            if other is not None and other != path:
                findings.append(
                    LintFinding(
                        severity=LintSeverity.WARNING,
                        finding_type="alias_collision",
                        file_path=str(path.relative_to(vault_root)),
                        page_id=str(data.get("id") or ""),
                        source_id=None,
                        message=(
                            f"alias '{alias}' clashes with title of "
                            f"'{other.relative_to(vault_root)}'"
                        ),
                    )
                )
    return findings


def _check_extracted_paths(conn: sqlite3.Connection, vault_root: Path) -> list[LintFinding]:
    findings: list[LintFinding] = []
    rows = conn.execute(
        "SELECT id, extracted_path FROM sources WHERE extracted_path IS NOT NULL"
    ).fetchall()
    for row in rows:
        ep = row["extracted_path"]
        if not ep:
            continue
        if not (vault_root / ep).exists():
            findings.append(
                LintFinding(
                    severity=LintSeverity.INFO,
                    finding_type="stale_extracted_path",
                    file_path=ep,
                    page_id=None,
                    source_id=str(row["id"]),
                    message=f"sources.extracted_path points to missing file: {ep}",
                )
            )
    return findings


def _persist_findings(conn: sqlite3.Connection, report: LintReport) -> None:
    """Speichert Lint-Run und Findings in der Registry."""
    conn.execute(
        """
        INSERT INTO lint_runs (
            id, started_at, finished_at, status, findings_count, errors_count, warnings_count
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            report.run_id,
            report.started_at.isoformat(timespec="seconds"),
            report.finished_at.isoformat(timespec="seconds"),
            "completed",
            len(report.findings),
            report.errors,
            report.warnings,
        ),
    )
    # Bekannte page-ids in DB (FK-Sicherheit: nur diese werden in lint_findings gespeichert)
    known_pages = {row["id"] for row in conn.execute("SELECT id FROM pages").fetchall()}
    known_sources = {row["id"] for row in conn.execute("SELECT id FROM sources").fetchall()}
    for i, finding in enumerate(report.findings):
        page_id = finding.page_id if finding.page_id in known_pages else None
        source_id = finding.source_id if finding.source_id in known_sources else None
        conn.execute(
            """
            INSERT INTO lint_findings (
                id, lint_run_id, severity, finding_type, page_id, source_id,
                file_path, message, status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                f"lf_{report.run_id}_{i:04d}",
                report.run_id,
                finding.severity.value,
                finding.finding_type,
                page_id,
                source_id,
                finding.file_path,
                finding.message,
                "open",
                report.finished_at.isoformat(timespec="seconds"),
            ),
        )


def run_lint(
    conn: sqlite3.Connection,
    *,
    paths: VaultPaths | None = None,
    persist: bool = True,
) -> LintReport:
    """Top-Level Lint-Run."""
    paths = paths or get_paths()
    started_at = datetime.now(tz=UTC)
    run_id = "lr_" + generate_run_id()

    findings: list[LintFinding] = []
    page_data: list[tuple[Path, dict, str]] = []

    for path in _walk_wiki_files(paths.wiki):
        data, file_findings = _check_frontmatter(path)
        findings.extend(file_findings)
        if data is None:
            continue
        try:
            text = path.read_text(encoding="utf-8")
            _, body = parse_frontmatter(text)
        except (OSError, FrontmatterError):
            body = ""
        page_data.append((path, data, body))
        findings.extend(_check_slug_path(path, data, paths.root))
        findings.extend(_check_sources(path, data, paths.root))
        findings.extend(_check_hard_facts(path, body, data, paths.root))
        findings.extend(_check_volatile(path, data, paths.root))
        findings.extend(_check_length(path, body, data, paths.root))

    findings.extend(_check_duplicate_titles([(p, d) for p, d, _ in page_data], paths.root))
    findings.extend(_check_wikilinks(page_data, paths.root))
    findings.extend(_check_alias_collisions([(p, d) for p, d, _ in page_data], paths.root))
    findings.extend(_check_orphan_pages(conn))
    findings.extend(_check_extracted_paths(conn, paths.root))

    finished_at = datetime.now(tz=UTC)
    report = LintReport(
        run_id=run_id,
        started_at=started_at,
        finished_at=finished_at,
        findings=findings,
    )
    if persist:
        _persist_findings(conn, report)
    return report


def write_report_markdown(report: LintReport, target_path: Path) -> None:
    """Schreibt einen Markdown-Report nach ``docs/_ops/lint_reports/<run_id>.md``."""
    lines = [
        f"# Lint Report — {report.run_id}",
        "",
        f"**Started:** {report.started_at.isoformat(timespec='seconds')}",
        f"**Finished:** {report.finished_at.isoformat(timespec='seconds')}",
        f"**Findings:** {len(report.findings)} "
        f"(errors: {report.errors}, warnings: {report.warnings}, info: {report.infos})",
        "",
    ]
    if not report.findings:
        lines.append("_(no findings)_")
    else:
        for finding in report.findings:
            lines.append(
                f"- **[{finding.severity.value}]** `{finding.finding_type}` — "
                f"{finding.file_path or finding.page_id or finding.source_id or '(no path)'}"
            )
            lines.append(f"  - {finding.message}")
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
