"""Pytest-Fixtures."""

from __future__ import annotations

import pytest
from click.testing import CliRunner


@pytest.fixture
def runner() -> CliRunner:
    """Click CLI Runner für CLI-Tests."""
    return CliRunner()
