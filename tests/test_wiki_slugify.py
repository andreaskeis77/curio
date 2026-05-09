"""Tests fuer Slugify-Helpers."""

from __future__ import annotations

from curiosity_wiki.wiki.slugify import disambiguate, slugify


def test_slugify_simple() -> None:
    assert slugify("Hello World") == "hello-world"


def test_slugify_german_umlauts() -> None:
    assert slugify("Über die Größe") == "ueber-die-groesse"
    assert slugify("Schöne Aussicht") == "schoene-aussicht"


def test_slugify_special_chars() -> None:
    assert slugify("Foo & Bar / Baz!") == "foo-bar-baz"


def test_slugify_french_accents() -> None:
    assert slugify("Café Été") == "cafe-ete"


def test_slugify_empty_returns_untitled() -> None:
    assert slugify("") == "untitled"
    assert slugify("---") == "untitled"
    assert slugify("   ") == "untitled"


def test_slugify_max_length() -> None:
    long_title = "x" * 200
    assert len(slugify(long_title, max_length=50)) <= 50


def test_disambiguate_no_collision() -> None:
    assert disambiguate("foo", set()) == "foo"


def test_disambiguate_collision() -> None:
    assert disambiguate("foo", {"foo"}) == "foo-2"
    assert disambiguate("foo", {"foo", "foo-2"}) == "foo-3"
