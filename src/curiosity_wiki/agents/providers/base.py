"""Provider-Basisinterface."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


class ProviderError(RuntimeError):
    """Wird bei Netzwerkfehlern, 429/5xx, Timeout, JSON-Decode-Fehler geworfen."""


@dataclass
class ProviderResponse:
    """Output eines Provider-Adapters."""

    parsed_payload: dict[str, Any]
    raw_text: str
    model: str | None
    token_usage: dict[str, int] = field(default_factory=dict)


class Provider(Protocol):
    """Schmale Schnittstelle, die alle Adapter erfüllen."""

    def complete(
        self,
        *,
        prompt_text: str,
        source_id: str,
        prompt_id: str,
        timeout: int,
        temperature: float,
        model: str | None,
    ) -> ProviderResponse: ...
