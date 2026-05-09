"""Publish-Pipeline (ADR-0012): Proposal -> Wiki-Pages.

Two-Phase:
- Phase A (Build): Lade Proposal, baue In-Memory-Pages, validiere Slugs.
- Phase B (Persist): Schreibe Files atomar, dann Registry-Updates, dann optional Git.
"""

from __future__ import annotations

import os
import re
import sqlite3
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path

import yaml

from curiosity_wiki.agents.schemas import IngestProposalV1
from curiosity_wiki.ids import generate_claim_id, generate_page_id
from curiosity_wiki.paths import VaultPaths, get_paths
from curiosity_wiki.proposals.repository import ProposalRepository
from curiosity_wiki.sources.repository import SourceRepository
from curiosity_wiki.wiki.atomic import atomic_write_text
from curiosity_wiki.wiki.frontmatter import FrontmatterError, parse_frontmatter, render_frontmatter
from curiosity_wiki.wiki.git_helper import GitHelperError, auto_commit_publish
from curiosity_wiki.wiki.models import (
    Claim,
    ConfidenceLevel,
    Freshness,
    Page,
    PageStatus,
    PageType,
    SourceRelation,
)
from curiosity_wiki.wiki.repository import (
    ClaimRepository,
    LinkRepository,
    PageRepository,
    PageSourceRepository,
)
from curiosity_wiki.wiki.slugify import disambiguate, slugify
from curiosity_wiki.wiki.source_page import build_source_page
from curiosity_wiki.wiki.templates import render_body

DEFAULT_REVIEW_DAYS = {
    Freshness.STABLE: None,
    Freshness.PERIODIC: 180,
    Freshness.VOLATILE: 90,
    Freshness.PERSONAL: None,
}

WIKILINK_RE = re.compile(r"\[\[([^\]]+?)\]\]")


def _extract_wikilink_targets(body: str) -> list[str]:
    """Liefert die Target-Texte (vor ``|``) aller ``[[...]]`` im Body."""
    targets: list[str] = []
    for match in WIKILINK_RE.finditer(body):
        target = match.group(1).split("|")[0].strip()
        if target:
            targets.append(target)
    return targets


class PublishError(RuntimeError):
    """Publish konnte nicht durchgefuehrt werden."""


class SlugCollisionError(PublishError):
    """Eine vorgeschlagene Page-Seite existiert bereits."""


@dataclass
class PublishResult:
    """Zusammenfassung eines Publish-Laufs."""

    proposal_id: str
    pages_written: list[str] = field(default_factory=list)  # relative paths
    page_ids: list[str] = field(default_factory=list)
    source_page_path: str | None = None
    claims_count: int = 0
    git_commit: str | None = None
    auto_commit_skipped_reason: str | None = None


def _now() -> datetime:
    return datetime.now(tz=UTC)


def _freshness_from_recommendation(
    recommendations: list, page_title: str, default: Freshness = Freshness.STABLE
) -> tuple[Freshness, datetime | None]:
    """Findet die Freshness-Empfehlung fuer einen Page-Titel."""
    for rec in recommendations:
        if rec.page_title.strip().lower() == page_title.strip().lower():
            f = Freshness(rec.freshness.value)
            review_after = None
            days = rec.review_after_days
            if days is None:
                days = DEFAULT_REVIEW_DAYS.get(f)
            if days:
                review_after = _now() + timedelta(days=days)
            return f, review_after
    return default, None


def _claims_for_page(
    proposal: IngestProposalV1,
    page_id: str,
    proposal_id: str,
    now: datetime,
) -> list[Claim]:
    return [
        Claim(
            id=generate_claim_id(),
            page_id=page_id,
            claim_text=fact.claim_text,
            claim_type=fact.claim_type,
            source_id=fact.source_id,
            confidence=ConfidenceLevel(fact.confidence.value),
            verified_at=now,
            proposal_id=proposal_id,
            created_at=now,
            updated_at=now,
        )
        for fact in proposal.hard_facts
    ]


def _claim_marker_lines(claims: list[Claim]) -> str:
    """Sektion ``Belegte Fakten`` mit Inline-Markern (ADR-0013)."""
    if not claims:
        return ""
    lines = ["## Belegte Fakten", ""]
    for claim in claims:
        lines.append(f"- {claim.claim_text}")
        lines.append(f"  - `claim:{claim.id} source:{claim.source_id} type:{claim.claim_type}`")
    lines.append("")
    return "\n".join(lines)


def _load_proposal_v1(proposal_dir: Path) -> tuple[IngestProposalV1, dict]:
    """Liest ``proposal.yaml`` und liefert das geparste Pydantic-Modell."""
    yaml_path = proposal_dir / "proposal.yaml"
    if not yaml_path.exists():
        raise PublishError(f"proposal.yaml not found in {proposal_dir}")
    payload = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise PublishError(f"proposal.yaml in {proposal_dir} is not a mapping")
    if "data" not in payload or not isinstance(payload["data"], dict):
        raise PublishError(f"proposal.yaml in {proposal_dir} missing 'data' field")
    try:
        proposal = IngestProposalV1.model_validate(payload["data"])
    except Exception as exc:
        raise PublishError(f"proposal.yaml schema validation failed: {exc}") from exc
    return proposal, payload


def publish_proposal(
    proposal_id: str,
    *,
    conn: sqlite3.Connection,
    paths: VaultPaths | None = None,
    auto_commit: bool | None = None,
) -> PublishResult:
    """Veroeffentlicht ein Proposal nach ``wiki/``.

    Phase A (Build): Validierung, kein Side Effect.
    Phase B (Persist): Atomic File Writes, Registry-Inserts, optional Git-Commit.
    """
    paths = paths or get_paths()
    if auto_commit is None:
        auto_commit = os.environ.get("CURIOSITY_PUBLISH_AUTO_COMMIT", "false").lower() in {
            "1",
            "true",
            "yes",
            "on",
        }

    proposal_repo = ProposalRepository(conn)
    page_repo = PageRepository(conn)
    page_source_repo = PageSourceRepository(conn)
    claim_repo = ClaimRepository(conn)
    link_repo = LinkRepository(conn)
    source_repo = SourceRepository(conn)

    record = proposal_repo.get(proposal_id)
    if record is None:
        raise PublishError(f"Proposal not found: {proposal_id}")
    if record.status not in {"pending", "needs_changes"}:
        raise PublishError(
            f"Proposal {proposal_id} is in status '{record.status}', "
            "only 'pending' or 'needs_changes' can be published."
        )

    proposal_dir = paths.root / record.path
    proposal_data, _raw_payload = _load_proposal_v1(proposal_dir)

    if record.source_id is None:
        raise PublishError(f"Proposal {proposal_id} has no source_id, cannot publish.")
    source = source_repo.get(record.source_id)
    if source is None:
        raise PublishError(f"Source {record.source_id} not found in registry.")

    now = _now()

    # --- Phase A: Build ---
    pages_to_write: list[tuple[Page, str]] = []  # (page, full_markdown)
    claims_to_write: list[Claim] = []

    # Source-Page (idempotent: nur einmal pro Source)
    existing_source_page = None
    for type_value in (PageType.SOURCE,):
        existing_source_page = page_repo.find_by_slug(
            slugify(source.title or source.id), type_value
        )
        if existing_source_page is not None:
            break

    source_page_path: str | None = None
    if existing_source_page is None:
        source_page, source_md = build_source_page(
            source,
            page_id=generate_page_id(),
            proposal_id=record.id,
            existing_slugs=page_repo.existing_slugs(PageType.SOURCE),
            now=now,
        )
        pages_to_write.append((source_page, source_md))
        source_page_path = source_page.relative_path
    else:
        source_page = existing_source_page
        source_page_path = existing_source_page.relative_path

    # Andere Pages aus proposal.new_pages
    slugs_per_type: dict[PageType, set[str]] = {}
    for proposed in proposal_data.new_pages:
        ptype_value = proposed.type.value
        try:
            ptype = PageType(ptype_value)
        except ValueError as exc:
            raise PublishError(f"Unknown page type: {ptype_value!r}") from exc
        if ptype == PageType.SOURCE:
            # Source-Pages werden separat gehandelt
            continue
        existing = slugs_per_type.setdefault(ptype, page_repo.existing_slugs(ptype))
        desired = proposed.slug or slugify(proposed.title)
        # Existiert die Page schon? Dann Skip mit Hinweis.
        if desired in existing:
            raise SlugCollisionError(
                f"Slug '{desired}' already exists for type '{ptype.value}'. "
                "M3 ueberschreibt nicht — bitte Proposal manuell anpassen oder Page editieren."
            )
        slug = disambiguate(desired, existing)
        existing.add(slug)

        page_id = generate_page_id()
        freshness, review_after = _freshness_from_recommendation(
            proposal_data.freshness_recommendations, proposed.title
        )
        page = Page(
            id=page_id,
            title=proposed.title,
            slug=slug,
            page_type=ptype,
            status=PageStatus.ACTIVE,
            freshness=freshness,
            confidence=ConfidenceLevel(proposed.confidence.value),
            created_at=now,
            updated_at=now,
            last_checked=now,
            review_after=review_after,
            proposal_id=record.id,
            sources=[source.id],
            why_interesting=proposed.why_interesting or "",
            llm_generated=True,
            human_reviewed=True,
            reviewed_at=now,
        )

        page_claims = [
            c
            for c in _claims_for_page(proposal_data, page_id, record.id, now)
            if c.source_id == source.id or any(c.source_id in proposed.sources for _ in [None])
        ]
        # Eigentlich nehmen wir alle hard_facts (LLM kann mehrere Sources referenzieren)
        page_claims = _claims_for_page(proposal_data, page_id, record.id, now)
        claims_to_write.extend(page_claims)

        sections = [(s.heading, s.markdown) for s in proposed.sections]
        body = render_body(
            ptype,
            proposed.title,
            sections,
            why_interesting=proposed.why_interesting or "",
        )
        if proposed.open_questions:
            body += "\n## Offene Fragen aus Proposal\n\n"
            for q in proposed.open_questions:
                body += f"- {q}\n"
            body += "\n"
        body += _claim_marker_lines(page_claims)
        # Quellen-Sektion am Ende
        body += "\n## Quellen\n\n"
        body += f"- [[{source.title or source.id}]] (`{source.id}`)\n"

        full = render_frontmatter(page) + "\n" + body
        pages_to_write.append((page, full))

    # --- Phase B: Persist ---
    written_paths: list[str] = []
    written_page_ids: list[str] = []
    try:
        for page, full_md in pages_to_write:
            target = paths.root / page.relative_path
            atomic_write_text(target, full_md)
            written_paths.append(page.relative_path)
            written_page_ids.append(page.id)

        # Registry: Pages, Page-Sources, Claims
        for page, _ in pages_to_write:
            # Source-Page kann existieren, dann skip-insert
            if page.id == (existing_source_page.id if existing_source_page else None):
                continue
            page_repo.insert(page)
            for src_id in page.sources or [source.id]:
                page_source_repo.link(page.id, src_id, SourceRelation.PRIMARY)
        for claim in claims_to_write:
            claim_repo.insert(claim)

        # Backlinks-Auto-Compute (M4): Wikilinks aus Body extrahieren und in `links` schreiben.
        # Idempotent: alte Links der Page zuerst loeschen (relevant fuer spaeteren Re-Publish-Pfad).
        for page, full_md in pages_to_write:
            try:
                _, body = parse_frontmatter(full_md)
            except FrontmatterError:
                body = full_md
            targets = _extract_wikilink_targets(body)
            link_repo.delete_for_page(page.id)
            for target in targets:
                target_page = page_repo.find_by_title(target)
                if target_page is not None:
                    link_repo.insert(
                        from_page_id=page.id,
                        to_page_id=target_page.id,
                        target_text=target,
                        status="resolved",
                    )
                else:
                    link_repo.insert(
                        from_page_id=page.id,
                        to_page_id=None,
                        target_text=target,
                        status="broken",
                    )

        # Proposal-Status auf approved
        proposal_repo.update_status(proposal_id, "approved", "approved by user")

        # Source-Status: indexed
        from curiosity_wiki.sources.models import SourceStatus

        conn.execute(
            "UPDATE sources SET status = ?, updated_at = ? WHERE id = ?",
            (SourceStatus.INDEXED.value, _now().isoformat(timespec="seconds"), source.id),
        )
    except Exception as exc:
        raise PublishError(f"Persist phase failed: {exc}") from exc

    # Optional: Auto-Commit
    git_commit_hash: str | None = None
    auto_commit_skipped_reason: str | None = None
    if auto_commit and written_paths:
        message = _commit_message(
            proposal_id=proposal_id,
            source_id=source.id,
            run_id=record.run_id or "n/a",
            pages=[(page.relative_path, page.page_type.value, "new") for page, _ in pages_to_write],
        )
        try:
            git_commit_hash = auto_commit_publish(
                repo_root=paths.root,
                relative_paths=written_paths,
                message=message,
                require_clean_other_changes=True,
            )
            if git_commit_hash is None:
                auto_commit_skipped_reason = (
                    "other uncommitted changes outside publish scope; commit manually"
                )
        except GitHelperError as exc:
            auto_commit_skipped_reason = f"git error: {exc}"

    return PublishResult(
        proposal_id=proposal_id,
        pages_written=written_paths,
        page_ids=written_page_ids,
        source_page_path=source_page_path,
        claims_count=len(claims_to_write),
        git_commit=git_commit_hash,
        auto_commit_skipped_reason=auto_commit_skipped_reason,
    )


def reject_proposal(
    proposal_id: str,
    *,
    conn: sqlite3.Connection,
    reason: str = "rejected by user",
) -> None:
    """Setzt Proposal-Status auf ``rejected``. Schreibt nichts nach wiki/."""
    proposal_repo = ProposalRepository(conn)
    record = proposal_repo.get(proposal_id)
    if record is None:
        raise PublishError(f"Proposal not found: {proposal_id}")
    proposal_repo.update_status(proposal_id, "rejected", reason)


def request_changes(
    proposal_id: str,
    *,
    conn: sqlite3.Connection,
    paths: VaultPaths | None = None,
    notes: str = "",
) -> None:
    """Setzt Proposal-Status auf ``needs_changes`` und schreibt review_notes.md."""
    paths = paths or get_paths()
    proposal_repo = ProposalRepository(conn)
    record = proposal_repo.get(proposal_id)
    if record is None:
        raise PublishError(f"Proposal not found: {proposal_id}")
    proposal_repo.update_status(proposal_id, "needs_changes", notes or "needs changes")
    if notes:
        target = paths.root / record.path / "review_notes.md"
        atomic_write_text(target, f"# Review Notes\n\n{notes}\n")


def _commit_message(
    *,
    proposal_id: str,
    source_id: str,
    run_id: str,
    pages: list[tuple[str, str, str]],
) -> str:
    lines = [
        f"publish: {proposal_id} -> {len(pages)} page(s) from {source_id}",
        "",
    ]
    for path, ptype, status in pages:
        lines.append(f"- {path} ({status}, type={ptype})")
    lines.extend(
        [
            "",
            f"Proposal: {proposal_id}",
            f"Source:   {source_id}",
            f"Run:      {run_id}",
        ]
    )
    return "\n".join(lines)
