"""Jinja2-Setup, Markdown-Rendering und Wikilink-Resolution."""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path

from fastapi.templating import Jinja2Templates
from markdown_it import MarkdownIt

TEMPLATES_DIR = Path(__file__).parent / "templates"
STATIC_DIR = Path(__file__).parent / "static"

WIKILINK_RE = re.compile(r"\[\[([^\]]+?)\]\]")


def get_templates() -> Jinja2Templates:
    """Singleton-Templates-Instanz."""
    return Jinja2Templates(directory=str(TEMPLATES_DIR))


def _markdown_renderer() -> MarkdownIt:
    md = MarkdownIt("commonmark", {"html": False, "linkify": True})
    md.enable(["table"])
    return md


_MD = _markdown_renderer()


def resolve_wikilinks(body: str, conn: sqlite3.Connection) -> str:
    """Ersetzt ``[[Title]]`` durch Markdown-Links auf ``/p/<slug>``.

    Unbekannte Targets werden als Text mit Klasse ``broken-link`` beibehalten.
    Dies geschieht **vor** dem Markdown-Render, damit der Link-Text korrekt
    HTML-escapet wird.
    """
    title_to_slug: dict[str, str] = {}
    for row in conn.execute("SELECT title, slug FROM pages WHERE status = 'active'").fetchall():
        title_to_slug[row["title"].lower()] = row["slug"]

    def replace(match: re.Match[str]) -> str:
        target = match.group(1).split("|")[0].strip()
        slug = title_to_slug.get(target.lower())
        if slug is None:
            return f'<span class="broken-link">[[{target}]]</span>'
        return f"[{target}](/p/{slug})"

    return WIKILINK_RE.sub(replace, body)


def render_markdown(body: str) -> str:
    """Markdown-Body zu HTML."""
    return _MD.render(body)


def render_body_with_links(body: str, conn: sqlite3.Connection) -> str:
    """Wikilinks resolven, dann Markdown rendern."""
    return render_markdown(resolve_wikilinks(body, conn))
