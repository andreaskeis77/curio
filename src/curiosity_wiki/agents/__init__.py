"""curiosity_wiki.agents — LLM-Client und Prompt-Registry.

Public API:

- ``LLMClient`` — Wrapper über Provider-Adapter.
- ``RunEvidence`` — Provenienz pro LLM-Call.
- ``PromptRegistry`` / ``PromptDefinition``.
- ``injection_findings`` — Prompt-Injection-Heuristik.
"""

from __future__ import annotations

from curiosity_wiki.agents.client import (
    LLMClient,
    LLMClientError,
    RunEvidence,
    SchemaValidationError,
)
from curiosity_wiki.agents.injection import injection_findings
from curiosity_wiki.agents.prompts import PromptDefinition, PromptRegistry

__all__ = [
    "LLMClient",
    "LLMClientError",
    "PromptDefinition",
    "PromptRegistry",
    "RunEvidence",
    "SchemaValidationError",
    "injection_findings",
]
