"""Mock-Provider — deterministisch, ohne Netzwerk.

Lädt eine Fixture aus ``tests/fixtures/llm_outputs/<prompt_id>/<source_id>.yaml``,
falls vorhanden. Sonst liefert er einen minimalen, schema-konformen Default
für ``ingest_v0_1`` (siehe ``DEFAULT_INGEST_OUTPUT``).

Die Fixture-Suche geht zuerst über ``CURIOSITY_VAULT_ROOT``-relative Pfade,
dann über den Repo-Root.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from curiosity_wiki.agents.providers.base import Provider, ProviderError, ProviderResponse
from curiosity_wiki.paths import get_vault_root

DEFAULT_INGEST_OUTPUT: dict[str, Any] = {
    "new_pages": [
        {
            "title": "Mock Topic",
            "slug": "mock-topic",
            "type": "topic",
            "sources": [],
            "sections": [
                {"heading": "Kurzfassung", "markdown": "Mock-generierter Standardinhalt."},
            ],
            "open_questions": ["Ist diese Quelle vertrauenswürdig?"],
            "why_interesting": "Default-Mock-Output ohne Fixture.",
            "confidence": "low",
        }
    ],
    "hard_facts": [],
    "open_questions": ["Was ist die Kern-Aussage dieser Quelle?"],
    "risk_notes": [
        {
            "risk_type": "hallucination_risk",
            "severity": "low",
            "description": "Mock-Output enthält keine echten Quellenanalysen.",
        }
    ],
    "freshness_recommendations": [],
    "overall_confidence": "low",
    "summary": "Mock-Default-Proposal.",
}


def _candidate_fixture_paths(prompt_id: str, source_id: str) -> list[Path]:
    """Mögliche Fixture-Pfade in Reihenfolge der Bevorzugung."""
    candidates: list[Path] = []
    # Test-Vault hat typischerweise tests/fixtures/llm_outputs/...
    vault = get_vault_root()
    candidates.append(
        vault / "tests" / "fixtures" / "llm_outputs" / prompt_id / f"{source_id}.yaml"
    )
    # Auch nach Source-ID-Prefix erlauben (z.B. fixtures/unesco_alhambra.yaml)
    candidates.append(
        vault / "tests" / "fixtures" / "llm_outputs" / prompt_id / "by_source" / f"{source_id}.yaml"
    )
    return candidates


def _load_fixture(prompt_id: str, source_id: str) -> dict[str, Any] | None:
    for candidate in _candidate_fixture_paths(prompt_id, source_id):
        if candidate.exists():
            try:
                data = yaml.safe_load(candidate.read_text(encoding="utf-8"))
            except yaml.YAMLError as exc:
                raise ProviderError(f"Mock fixture {candidate} not valid YAML: {exc}") from exc
            if not isinstance(data, dict):
                raise ProviderError(f"Mock fixture {candidate} must be a mapping")
            return data
    return None


class MockProvider(Provider):
    """Deterministischer Stub-Provider."""

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
        # Nutze das Fixture, falls vorhanden — sonst Default.
        payload = _load_fixture(prompt_id, source_id)
        if payload is None:
            payload = DEFAULT_INGEST_OUTPUT
        raw_text = yaml.safe_dump(payload, allow_unicode=True, sort_keys=False)
        return ProviderResponse(
            parsed_payload=payload,
            raw_text=raw_text,
            model="mock-1",
            token_usage={"input_tokens": len(prompt_text), "output_tokens": len(raw_text)},
        )
