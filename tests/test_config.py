"""Tests für Config-Loader."""

from __future__ import annotations

import pytest

from curiosity_wiki.config import CuriosityConfig, load_config


def test_config_defaults_in_clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in [
        "CURIOSITY_LLM_PROVIDER",
        "CURIOSITY_LLM_MODEL",
        "CURIOSITY_LLM_TEMPERATURE",
        "CURIOSITY_LLM_TIMEOUT_SECONDS",
        "CURIOSITY_LOG_LEVEL",
        "CURIOSITY_LOG_FORMAT",
        "CURIOSITY_WEB_HOST",
        "CURIOSITY_WEB_PORT",
        "CURIOSITY_DEV_FAIL_FAST",
        "CURIOSITY_AGENT_DRY_RUN",
    ]:
        monkeypatch.delenv(key, raising=False)
    cfg = load_config()
    assert isinstance(cfg, CuriosityConfig)
    assert cfg.llm_provider == "mock"
    assert cfg.llm_temperature == 0
    assert cfg.web_host == "127.0.0.1"
    assert cfg.web_port == 8765
    assert cfg.dev_fail_fast is True
    assert cfg.agent_dry_run is True


def test_config_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CURIOSITY_LLM_PROVIDER", "anthropic")
    monkeypatch.setenv("CURIOSITY_LLM_TEMPERATURE", "1")
    monkeypatch.setenv("CURIOSITY_WEB_PORT", "9000")
    monkeypatch.setenv("CURIOSITY_DEV_FAIL_FAST", "false")
    cfg = load_config()
    assert cfg.llm_provider == "anthropic"
    assert cfg.llm_temperature == 1
    assert cfg.web_port == 9000
    assert cfg.dev_fail_fast is False


def test_config_invalid_int_falls_back(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CURIOSITY_WEB_PORT", "not-a-number")
    cfg = load_config()
    assert cfg.web_port == 8765


def test_config_bool_parsing(monkeypatch: pytest.MonkeyPatch) -> None:
    for value in ("1", "true", "TRUE", "yes", "on"):
        monkeypatch.setenv("CURIOSITY_AGENT_DRY_RUN", value)
        assert load_config().agent_dry_run is True
    for value in ("0", "false", "no", "off"):
        monkeypatch.setenv("CURIOSITY_AGENT_DRY_RUN", value)
        assert load_config().agent_dry_run is False
