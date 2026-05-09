"""Prompt-Registry: Datei-basierte Prompts mit Hash und Frontmatter.

Format pro Prompt-Datei (siehe ADR-0010):

```markdown
---
prompt_id: ingest_v0_1
purpose: "..."
schema_version: 1
inputs:
  - source_metadata
  - extracted_content
created: 2026-05-08
---

<Prompt-Body>
```

Der Hash deckt nur den **Body** ab, nicht das Frontmatter — damit
metadata-Änderungen (z.B. Korrektur von `purpose`) keinen neuen Prompt
erzeugen.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


class PromptError(RuntimeError):
    """Prompt-Datei-Fehler."""


@dataclass(frozen=True)
class PromptDefinition:
    """Geladenes Prompt mit Metadaten."""

    prompt_id: str
    file_path: Path
    body: str
    purpose: str
    schema_version: int
    inputs: list[str]
    prompt_hash: str

    def render(self, inputs: dict[str, str]) -> str:
        """Substituiert ``{var}``-Platzhalter im Body durch ``inputs[var]``.

        Bei fehlendem Key wird ein leerer String eingesetzt — wir nehmen die
        permissivere Variante, weil Prompts auch ohne alle Inputs lauffähig sein
        sollen (z.B. wenn nur source_metadata, kein extracted_content).
        """
        text = self.body
        for key, value in inputs.items():
            text = text.replace("{" + key + "}", value)
        return text


def _parse_prompt_file(path: Path) -> PromptDefinition:
    raw = path.read_text(encoding="utf-8")
    match = FRONTMATTER_RE.match(raw)
    if not match:
        raise PromptError(f"Prompt file missing frontmatter: {path}")
    front_text = match.group(1)
    body = raw[match.end() :]
    try:
        front: dict[str, Any] = yaml.safe_load(front_text) or {}
    except yaml.YAMLError as exc:
        raise PromptError(f"Invalid YAML frontmatter in {path}: {exc}") from exc

    prompt_id = front.get("prompt_id")
    if not prompt_id or not isinstance(prompt_id, str):
        raise PromptError(f"Prompt file missing prompt_id: {path}")

    purpose = str(front.get("purpose", ""))
    schema_version = int(front.get("schema_version", 1))
    inputs_raw = front.get("inputs") or []
    if not isinstance(inputs_raw, list):
        raise PromptError(f"Prompt {prompt_id}: 'inputs' must be a list")
    inputs = [str(x) for x in inputs_raw]

    body_normalized = body.strip() + "\n"
    prompt_hash = hashlib.sha256(body_normalized.encode("utf-8")).hexdigest()

    return PromptDefinition(
        prompt_id=prompt_id,
        file_path=path,
        body=body_normalized,
        purpose=purpose,
        schema_version=schema_version,
        inputs=inputs,
        prompt_hash=prompt_hash,
    )


@dataclass
class PromptRegistry:
    """Loader und Cache für Prompts.

    Wird beim Erzeugen einmal initialisiert und ist damit deterministisch
    pro Process-Lifetime. Re-Load nur durch Neu-Initialisierung.
    """

    prompts_dir: Path
    _cache: dict[str, PromptDefinition]

    @classmethod
    def from_dir(cls, prompts_dir: Path) -> PromptRegistry:
        """Lädt alle Prompt-Dateien. README/Notizen ohne Frontmatter werden still übersprungen."""
        cache: dict[str, PromptDefinition] = {}
        if prompts_dir.exists():
            for file in sorted(prompts_dir.rglob("*.md")):
                if not file.is_file():
                    continue
                try:
                    definition = _parse_prompt_file(file)
                except PromptError:
                    # README.md, Notizen ohne YAML-Frontmatter: kein Prompt
                    continue
                cache[definition.prompt_id] = definition
        return cls(prompts_dir=prompts_dir, _cache=cache)

    def get(self, prompt_id: str) -> PromptDefinition:
        if prompt_id not in self._cache:
            raise PromptError(f"Unknown prompt_id: {prompt_id}")
        return self._cache[prompt_id]

    def all(self) -> list[PromptDefinition]:
        return list(self._cache.values())
