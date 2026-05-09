"""Anthropic-Provider-Adapter.

Wickelt ``anthropic.Anthropic().messages.create(...)``. Erwartet, dass das
Output-Modell JSON nach dem Pattern ``<json>...</json>`` oder im Fall von
Tool-Use-API direkt JSON liefert.

Für M2 nehmen wir den einfachen Fall: System-Prompt schreibt vor, dass die
Antwort ausschließlich JSON ist. Das funktioniert mit Claude zuverlässig,
solange der Prompt klar formuliert ist.
"""

from __future__ import annotations

import json
import os
from typing import Any

from curiosity_wiki.agents.providers.base import Provider, ProviderError, ProviderResponse

DEFAULT_MODEL = "claude-sonnet-4-6"


class AnthropicProvider(Provider):
    """Echter Anthropic-Provider. Importiert die SDK lazy."""

    def complete(
        self,
        *,
        prompt_text: str,
        source_id: str,
        prompt_id: str,
        timeout: int,
        temperature: float,
        model: str | None,
    ) -> ProviderResponse:
        try:
            import anthropic
        except ImportError as exc:
            raise ProviderError(
                "anthropic SDK not installed. Install via 'pip install anthropic'."
            ) from exc

        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise ProviderError("ANTHROPIC_API_KEY environment variable is not set.")

        client = anthropic.Anthropic(api_key=api_key, timeout=timeout)
        try:
            response = client.messages.create(
                model=model or DEFAULT_MODEL,
                max_tokens=4096,
                temperature=temperature,
                system=(
                    "Antworte ausschließlich mit gültigem JSON, das dem Output-Schema "
                    "des Aufrufers entspricht. Verwende keine Code-Fences."
                ),
                messages=[{"role": "user", "content": prompt_text}],
            )
        except anthropic.APIError as exc:
            raise ProviderError(f"Anthropic API error: {exc}") from exc

        text_blocks = [b.text for b in response.content if hasattr(b, "text")]
        raw_text = "\n".join(text_blocks).strip()
        try:
            parsed: Any = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            raise ProviderError(
                f"Anthropic response is not valid JSON: {exc}\nFirst 200 chars: {raw_text[:200]}"
            ) from exc
        if not isinstance(parsed, dict):
            raise ProviderError("Anthropic response is JSON but not an object")

        usage_obj = getattr(response, "usage", None)
        token_usage: dict[str, int] = {}
        if usage_obj is not None:
            token_usage = {
                "input_tokens": getattr(usage_obj, "input_tokens", 0),
                "output_tokens": getattr(usage_obj, "output_tokens", 0),
            }
        return ProviderResponse(
            parsed_payload=parsed,
            raw_text=raw_text,
            model=getattr(response, "model", model or DEFAULT_MODEL),
            token_usage=token_usage,
        )
