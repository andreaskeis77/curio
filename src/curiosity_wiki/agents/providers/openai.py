"""OpenAI-Provider-Adapter (Chat-Completions API mit JSON-Mode)."""

from __future__ import annotations

import json
import os
from typing import Any

from curiosity_wiki.agents.providers.base import Provider, ProviderError, ProviderResponse

DEFAULT_MODEL = "gpt-4o-mini"


class OpenAIProvider(Provider):
    """OpenAI Chat Completions mit ``response_format={'type': 'json_object'}``."""

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
            import openai
        except ImportError as exc:
            raise ProviderError(
                "openai SDK not installed. Install via 'pip install openai'."
            ) from exc

        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ProviderError("OPENAI_API_KEY environment variable is not set.")

        client = openai.OpenAI(api_key=api_key, timeout=timeout)
        try:
            response = client.chat.completions.create(
                model=model or DEFAULT_MODEL,
                temperature=temperature,
                response_format={"type": "json_object"},
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Antworte ausschließlich mit gültigem JSON entsprechend "
                            "dem Schema im User-Prompt."
                        ),
                    },
                    {"role": "user", "content": prompt_text},
                ],
            )
        except openai.APIError as exc:
            raise ProviderError(f"OpenAI API error: {exc}") from exc

        choice = response.choices[0]
        raw_text = (choice.message.content or "").strip()
        try:
            parsed: Any = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            raise ProviderError(
                f"OpenAI response is not valid JSON: {exc}\nFirst 200 chars: {raw_text[:200]}"
            ) from exc
        if not isinstance(parsed, dict):
            raise ProviderError("OpenAI response is JSON but not an object")

        usage = response.usage
        token_usage: dict[str, int] = {}
        if usage is not None:
            token_usage = {
                "input_tokens": usage.prompt_tokens,
                "output_tokens": usage.completion_tokens,
            }
        return ProviderResponse(
            parsed_payload=parsed,
            raw_text=raw_text,
            model=getattr(response, "model", model or DEFAULT_MODEL),
            token_usage=token_usage,
        )
