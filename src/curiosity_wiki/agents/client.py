"""LLM-Client-Wrapper (ADR-0010).

Lädt Prompt aus Registry, ruft Provider-Adapter, validiert Output gegen
Pydantic-Schema, schreibt ``ingest_runs``-Zeile (Run Evidence).
"""

from __future__ import annotations

import json
import sqlite3
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Protocol

from pydantic import BaseModel, ValidationError

from curiosity_wiki.agents.prompts import PromptDefinition, PromptRegistry
from curiosity_wiki.agents.providers import get_provider
from curiosity_wiki.agents.providers.base import ProviderError
from curiosity_wiki.config import CuriosityConfig
from curiosity_wiki.ids import generate_run_id


class LLMClientError(RuntimeError):
    """Fehler im LLM-Wrapper."""


class SchemaValidationError(LLMClientError):
    """Output entspricht nicht dem Pydantic-Schema (auch nach Retry)."""


@dataclass
class RunEvidence:
    """Provenienz pro LLM-Call."""

    run_id: str
    source_id: str
    prompt_id: str
    prompt_hash: str
    provider: str
    model: str | None
    temperature: float | None
    max_tokens: int | None
    started_at: datetime
    finished_at: datetime
    status: str
    token_usage: dict[str, int] = field(default_factory=dict)
    error_message: str | None = None


class IngestRunRecorder(Protocol):
    """Schmale Schnittstelle, damit Tests ohne DB laufen können."""

    def record(self, evidence: RunEvidence) -> None: ...


@dataclass
class SqliteIngestRunRecorder:
    """Persistiert Run Evidence in der ``ingest_runs``-Tabelle."""

    conn: sqlite3.Connection

    def record(self, evidence: RunEvidence) -> None:
        self.conn.execute(
            """
            INSERT INTO ingest_runs (
                id, source_id, prompt_id, prompt_hash, provider, model,
                temperature, max_tokens, started_at, finished_at, status,
                token_usage_json, error_message
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                evidence.run_id,
                evidence.source_id,
                evidence.prompt_id,
                evidence.prompt_hash,
                evidence.provider,
                evidence.model,
                evidence.temperature,
                evidence.max_tokens,
                evidence.started_at.isoformat(timespec="seconds"),
                evidence.finished_at.isoformat(timespec="seconds"),
                evidence.status,
                json.dumps(evidence.token_usage) if evidence.token_usage else None,
                evidence.error_message,
            ),
        )


@dataclass
class LLMClient:
    """Provider-agnostischer Wrapper."""

    registry: PromptRegistry
    config: CuriosityConfig
    recorder: IngestRunRecorder | None = None

    def complete(
        self,
        prompt_id: str,
        *,
        source_id: str,
        inputs: dict[str, str],
        output_schema: type[BaseModel],
        timeout: int | None = None,
        max_retries: int = 1,
    ) -> tuple[BaseModel, RunEvidence]:
        """Render → call → validate → persist."""
        definition = self.registry.get(prompt_id)
        provider = get_provider(self.config.llm_provider)

        run_id = generate_run_id()
        started_at = datetime.now(tz=UTC)
        prompt_text = definition.render(inputs)
        timeout_value = timeout if timeout is not None else self.config.llm_timeout_seconds

        attempts = 0
        last_error: Exception | None = None
        provider_response = None
        while attempts <= max_retries:
            attempts += 1
            try:
                provider_response = provider.complete(
                    prompt_text=prompt_text,
                    source_id=source_id,
                    prompt_id=prompt_id,
                    timeout=timeout_value,
                    temperature=float(self.config.llm_temperature),
                    model=self.config.llm_model or None,
                )
                break
            except ProviderError as exc:
                last_error = exc
                if attempts > max_retries:
                    break
                # exponential backoff: 1s, 4s
                time.sleep(1 if attempts == 1 else 4)
        if provider_response is None:
            finished_at = datetime.now(tz=UTC)
            evidence = RunEvidence(
                run_id=run_id,
                source_id=source_id,
                prompt_id=prompt_id,
                prompt_hash=definition.prompt_hash,
                provider=self.config.llm_provider,
                model=self.config.llm_model or None,
                temperature=float(self.config.llm_temperature),
                max_tokens=None,
                started_at=started_at,
                finished_at=finished_at,
                status="failed",
                error_message=str(last_error) if last_error else "provider call failed",
            )
            if self.recorder is not None:
                self.recorder.record(evidence)
            raise LLMClientError(
                f"Provider {self.config.llm_provider} failed after {attempts} attempts: "
                f"{last_error}"
            ) from last_error

        try:
            validated = output_schema.model_validate(provider_response.parsed_payload)
        except ValidationError as exc:
            finished_at = datetime.now(tz=UTC)
            evidence = RunEvidence(
                run_id=run_id,
                source_id=source_id,
                prompt_id=prompt_id,
                prompt_hash=definition.prompt_hash,
                provider=self.config.llm_provider,
                model=provider_response.model or self.config.llm_model,
                temperature=float(self.config.llm_temperature),
                max_tokens=None,
                started_at=started_at,
                finished_at=finished_at,
                status="failed",
                token_usage=provider_response.token_usage,
                error_message=f"schema_validation: {exc.errors()[:3]}",
            )
            if self.recorder is not None:
                self.recorder.record(evidence)
            raise SchemaValidationError(
                f"Output schema {output_schema.__name__} validation failed: {exc}"
            ) from exc

        finished_at = datetime.now(tz=UTC)
        evidence = RunEvidence(
            run_id=run_id,
            source_id=source_id,
            prompt_id=prompt_id,
            prompt_hash=definition.prompt_hash,
            provider=self.config.llm_provider,
            model=provider_response.model or self.config.llm_model,
            temperature=float(self.config.llm_temperature),
            max_tokens=None,
            started_at=started_at,
            finished_at=finished_at,
            status="completed",
            token_usage=provider_response.token_usage,
        )
        if self.recorder is not None:
            self.recorder.record(evidence)
        return validated, evidence


def register_prompt_in_db(
    conn: sqlite3.Connection,
    definition: PromptDefinition,
) -> None:
    """Schreibt das Prompt in ``agent_prompts`` (Upsert)."""
    conn.execute(
        """
        INSERT INTO agent_prompts (prompt_id, prompt_hash, purpose, schema_version,
                                   file_path, registered_at)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(prompt_id) DO UPDATE SET
            prompt_hash = excluded.prompt_hash,
            purpose = excluded.purpose,
            schema_version = excluded.schema_version,
            file_path = excluded.file_path,
            registered_at = excluded.registered_at
        """,
        (
            definition.prompt_id,
            definition.prompt_hash,
            definition.purpose,
            definition.schema_version,
            str(definition.file_path),
            datetime.now(tz=UTC).isoformat(timespec="seconds"),
        ),
    )
