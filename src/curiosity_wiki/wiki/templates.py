"""Markdown-Templates pro PageType.

Pro Typ ein konsistenter Body mit Sektionen, die der LLM-Output (oder ein
Mensch) auffuellen kann. Templates sind bewusst minimal und Obsidian-kompatibel.
"""

from __future__ import annotations

from curiosity_wiki.wiki.models import PageType


def _section(heading: str, body: str = "") -> str:
    return f"## {heading}\n\n{body.strip() or '_(zu ergaenzen)_'}\n"


def _body_topic(sections: list[tuple[str, str]]) -> str:
    standard = ["Kurzfassung", "Warum interessant?", "Zentrale Begriffe", "Kontext", "Verbindungen"]
    parts = [*_merge(sections, standard), _section("Offene Fragen"), _section("Quellen")]
    return "\n".join(parts)


def _body_place(sections: list[tuple[str, str]]) -> str:
    standard = [
        "Kurzfassung",
        "Lage und Kontext",
        "Bedeutung",
        "Besuchs-/Reisebezug",
        "Verbindungen",
    ]
    parts = [*_merge(sections, standard), _section("Offene Fragen"), _section("Quellen")]
    return "\n".join(parts)


def _body_person(sections: list[tuple[str, str]]) -> str:
    standard = ["Kurzfassung", "Biografie", "Werk und Wirken", "Verbindungen"]
    parts = [*_merge(sections, standard), _section("Offene Fragen"), _section("Quellen")]
    return "\n".join(parts)


def _body_recipe(sections: list[tuple[str, str]]) -> str:
    standard = [
        "Ziel",
        "Zutaten",
        "Methode",
        "Pacojet-Parameter",
        "Varianten",
        "Fehlerbilder",
        "Eigene Notizen",
        "Verbindungen",
    ]
    parts = [*_merge(sections, standard), _section("Quellen")]
    return "\n".join(parts)


def _body_method(sections: list[tuple[str, str]]) -> str:
    standard = ["Kurzfassung", "Anwendungsbereich", "Vorgehen", "Fehlerbilder", "Verbindungen"]
    parts = [*_merge(sections, standard), _section("Offene Fragen"), _section("Quellen")]
    return "\n".join(parts)


def _body_experiment(sections: list[tuple[str, str]]) -> str:
    standard = [
        "Fragestellung",
        "Setup",
        "Durchfuehrung",
        "Ergebnis",
        "Was hat funktioniert?",
        "Was hat nicht funktioniert?",
        "Naechster Versuch",
    ]
    parts = _merge(sections, standard)
    return "\n".join(parts)


def _body_product_research(sections: list[tuple[str, str]]) -> str:
    standard = [
        "Meine Anforderungen",
        "Wichtige Kaufkriterien",
        "Quellenlage",
        "Modelle / Optionen",
        "Vorlaeufige Einschaetzung",
        "Was muss erneut geprueft werden?",
    ]
    parts = [*_merge(sections, standard), _section("Quellen")]
    return "\n".join(parts)


def _body_event(sections: list[tuple[str, str]]) -> str:
    standard = ["Kurzfassung", "Datum / Periode", "Bedeutung", "Verbindungen"]
    parts = [*_merge(sections, standard), _section("Offene Fragen"), _section("Quellen")]
    return "\n".join(parts)


def _body_collection(sections: list[tuple[str, str]]) -> str:
    standard = ["Kriterien", "Mitglieder", "Notizen"]
    parts = [*_merge(sections, standard), _section("Quellen")]
    return "\n".join(parts)


def _body_question(sections: list[tuple[str, str]]) -> str:
    standard = ["Frage", "Stand der Recherche", "Verwandte Seiten"]
    parts = [*_merge(sections, standard), _section("Quellen")]
    return "\n".join(parts)


def _body_work(sections: list[tuple[str, str]]) -> str:
    standard = ["Kurzfassung", "Inhalt / Konzept", "Bedeutung", "Verbindungen"]
    parts = [*_merge(sections, standard), _section("Quellen")]
    return "\n".join(parts)


def _body_brand(sections: list[tuple[str, str]]) -> str:
    standard = ["Kurzfassung", "Geschichte", "Produkte / Linien", "Verbindungen"]
    parts = [*_merge(sections, standard), _section("Quellen")]
    return "\n".join(parts)


def _merge(provided: list[tuple[str, str]], standard: list[str]) -> list[str]:
    """Provided-Sections in Standard-Reihenfolge sortieren, Rest anhängen."""
    by_heading = {h.lower(): (h, b) for h, b in provided}
    out: list[str] = []
    used: set[str] = set()
    for std in standard:
        h, b = by_heading.get(std.lower(), (std, ""))
        out.append(_section(h, b))
        used.add(std.lower())
    # Provided-Sections, die nicht im Standard sind, ans Ende
    for h, b in provided:
        if h.lower() not in used:
            out.append(_section(h, b))
            used.add(h.lower())
    return out


_BUILDERS = {
    PageType.TOPIC: _body_topic,
    PageType.PLACE: _body_place,
    PageType.PERSON: _body_person,
    PageType.RECIPE: _body_recipe,
    PageType.METHOD: _body_method,
    PageType.EXPERIMENT: _body_experiment,
    PageType.PRODUCT_RESEARCH: _body_product_research,
    PageType.EVENT: _body_event,
    PageType.COLLECTION: _body_collection,
    PageType.QUESTION: _body_question,
    PageType.WORK: _body_work,
    PageType.BRAND: _body_brand,
}


def render_body(
    page_type: PageType,
    title: str,
    sections: list[tuple[str, str]],
    *,
    why_interesting: str = "",
) -> str:
    """Rendert das Markdown-Body (ohne Frontmatter) fuer eine Page."""
    builder = _BUILDERS.get(page_type)
    intro = f"# {title}\n"
    if why_interesting:
        intro += f"\n> {why_interesting}\n"
    if builder is None:
        # Source-Pages bekommen ihren eigenen Renderer in source_page.py
        return intro + "\n"
    return intro + "\n" + builder(sections) + "\n"
