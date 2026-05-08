"""Smoke tests — sicherstellen, dass das Paket überhaupt lädt."""

from __future__ import annotations

import curiosity_wiki


def test_package_imports() -> None:
    assert hasattr(curiosity_wiki, "__version__")


def test_version_is_string() -> None:
    assert isinstance(curiosity_wiki.__version__, str)
    assert curiosity_wiki.__version__.count(".") >= 2
