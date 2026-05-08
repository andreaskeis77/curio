"""Curiosity-Konfiguration aus Umgebungsvariablen.

Werte werden lazy geladen. Defaults sind sichere Werte für Dev/Tests.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


def _env_str(key: str, default: str) -> str:
    return os.environ.get(key, default)


def _env_int(key: str, default: int) -> int:
    raw = os.environ.get(key)
    if raw is None or raw == "":
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _env_bool(key: str, default: bool) -> bool:
    raw = os.environ.get(key)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class CuriosityConfig:
    """Reine Daten — keine Logik, keine Side Effects."""

    llm_provider: str
    llm_model: str
    llm_temperature: int  # bewusst int (0 ist Default)
    llm_timeout_seconds: int
    log_level: str
    log_format: str
    web_host: str
    web_port: int
    dev_fail_fast: bool
    agent_dry_run: bool


def load_config() -> CuriosityConfig:
    """Lädt Config aus Umgebung. ``.env`` wird vom CLI vorab geladen."""
    return CuriosityConfig(
        llm_provider=_env_str("CURIOSITY_LLM_PROVIDER", "mock"),
        llm_model=_env_str("CURIOSITY_LLM_MODEL", ""),
        llm_temperature=_env_int("CURIOSITY_LLM_TEMPERATURE", 0),
        llm_timeout_seconds=_env_int("CURIOSITY_LLM_TIMEOUT_SECONDS", 60),
        log_level=_env_str("CURIOSITY_LOG_LEVEL", "INFO"),
        log_format=_env_str("CURIOSITY_LOG_FORMAT", "text"),
        web_host=_env_str("CURIOSITY_WEB_HOST", "127.0.0.1"),
        web_port=_env_int("CURIOSITY_WEB_PORT", 8765),
        dev_fail_fast=_env_bool("CURIOSITY_DEV_FAIL_FAST", default=True),
        agent_dry_run=_env_bool("CURIOSITY_AGENT_DRY_RUN", default=True),
    )
