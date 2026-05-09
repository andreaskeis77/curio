"""Slug-Erzeugung mit deutschen Umlauten und Kollision-Suffixes."""

from __future__ import annotations

import re

# Deutsche Umlaut-Translit
TRANSLIT = {
    "ä": "ae",
    "ö": "oe",
    "ü": "ue",
    "Ä": "Ae",
    "Ö": "Oe",
    "Ü": "Ue",
    "ß": "ss",
    "À": "A",
    "Á": "A",
    "Â": "A",
    "Ã": "A",
    "à": "a",
    "á": "a",
    "â": "a",
    "ã": "a",
    "Ç": "C",
    "ç": "c",
    "È": "E",
    "É": "E",
    "Ê": "E",
    "è": "e",
    "é": "e",
    "ê": "e",
    "ë": "e",
    "Í": "I",
    "Î": "I",
    "í": "i",
    "î": "i",
    "ï": "i",
    "Ñ": "N",
    "ñ": "n",
    "Ó": "O",
    "Ô": "O",
    "Õ": "O",
    "ó": "o",
    "ô": "o",
    "õ": "o",
    "Ú": "U",
    "ú": "u",
    "û": "u",
}

NON_ALNUM = re.compile(r"[^a-z0-9]+")


def slugify(text: str, *, max_length: int = 80) -> str:
    """Wandelt einen Titel in einen kebab-case-Slug.

    - Deutsche Umlaute werden phonetisch umgeschrieben (ae/oe/ue/ss).
    - Andere Akzente werden auf ASCII reduziert.
    - Mehrfache Trenner werden zu einem ``-``.
    - Maximale Laenge ``max_length`` (default 80).
    """
    if not text:
        return "untitled"
    transliterated = "".join(TRANSLIT.get(ch, ch) for ch in text)
    lowered = transliterated.lower()
    slug = NON_ALNUM.sub("-", lowered).strip("-")
    if not slug:
        return "untitled"
    if len(slug) > max_length:
        slug = slug[:max_length].rstrip("-")
    return slug or "untitled"


def disambiguate(slug: str, taken: set[str]) -> str:
    """Falls ``slug`` bereits in ``taken``, hänge ``-2``, ``-3``, ... an."""
    if slug not in taken:
        return slug
    i = 2
    while True:
        candidate = f"{slug}-{i}"
        if candidate not in taken:
            return candidate
        i += 1
