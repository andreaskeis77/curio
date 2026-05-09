"""Heuristische Prompt-Injection-Erkennung (ADR-0011).

Reagiert auf bekannte Muster, die in Webquellen versuchen, den
LLM-System-Prompt zu kapern.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

INJECTION_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("ignore_previous", re.compile(r"\b(ignore|disregard)\s+(all\s+)?previous\b", re.IGNORECASE)),
    ("system_override", re.compile(r"\b(you\s+are\s+now|act\s+as)\s+\w+", re.IGNORECASE)),
    ("system_prompt_leak", re.compile(r"system\s+prompt", re.IGNORECASE)),
    ("token_smuggling", re.compile(r"<\|.*?\|>")),
    (
        "developer_role_swap",
        re.compile(r"\b(developer|admin)\s+(mode|override|access)\b", re.IGNORECASE),
    ),
    ("instructions_to_assistant", re.compile(r"\b(you\s+must|do\s+not\s+follow)\b", re.IGNORECASE)),
]


@dataclass(frozen=True)
class InjectionFinding:
    """Ein erkanntes Injection-Muster."""

    pattern_name: str
    snippet: str
    line_number: int


def injection_findings(text: str, max_findings: int = 20) -> list[InjectionFinding]:
    """Scannt ``text`` und liefert Treffer für die definierten Muster."""
    findings: list[InjectionFinding] = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        for name, pattern in INJECTION_PATTERNS:
            if pattern.search(line):
                findings.append(
                    InjectionFinding(
                        pattern_name=name,
                        snippet=line.strip()[:160],
                        line_number=line_no,
                    )
                )
                if len(findings) >= max_findings:
                    return findings
    return findings
