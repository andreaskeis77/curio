"""LLM-Provider-Adapter (mock / anthropic / openai)."""

from __future__ import annotations

from curiosity_wiki.agents.providers.base import (
    Provider,
    ProviderError,
    ProviderResponse,
)


def get_provider(name: str) -> Provider:
    """Factory: liefert Provider-Instanz nach Name."""
    if name == "mock":
        from curiosity_wiki.agents.providers.mock import MockProvider

        return MockProvider()
    if name == "anthropic":
        from curiosity_wiki.agents.providers.anthropic import AnthropicProvider

        return AnthropicProvider()
    if name == "openai":
        from curiosity_wiki.agents.providers.openai import OpenAIProvider

        return OpenAIProvider()
    raise ProviderError(f"Unknown provider: {name}. Use mock|anthropic|openai.")


__all__ = ["Provider", "ProviderError", "ProviderResponse", "get_provider"]
