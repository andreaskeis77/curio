"""Zentrale Path-Abstraktion.

Alle Pfade des Curiosity-Vaults werden hier abgeleitet — kein Modul
darf Pfade hardcodieren. Die Vault-Wurzel kann via Umgebungsvariable
``CURIOSITY_VAULT_ROOT`` überschrieben werden, sonst gilt die Repo-Wurzel
(zwei Ebenen über dieser Datei).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _detect_repo_root() -> Path:
    """Repo root = dir, das `pyproject.toml` enthält, ausgehend vom Modul-Pfad."""
    here = Path(__file__).resolve()
    for parent in [here, *here.parents]:
        if (parent / "pyproject.toml").exists():
            return parent
    # Fallback: 3 Ebenen hoch (src/curiosity_wiki/paths.py -> repo root)
    return here.parents[2]


def get_vault_root() -> Path:
    """Liefert die Vault-Wurzel (Repo-Root oder ``CURIOSITY_VAULT_ROOT``)."""
    override = os.environ.get("CURIOSITY_VAULT_ROOT")
    if override:
        return Path(override).expanduser().resolve()
    return _detect_repo_root()


@dataclass(frozen=True)
class VaultPaths:
    """Sammlung aller relevanten Vault-Pfade.

    Jeder Pfad ist absolut und auf der aktuellen Plattform korrekt.
    Pfade werden **nicht** automatisch erstellt — wer schreiben will,
    erstellt das Verzeichnis selbst (klare Verantwortung).
    """

    root: Path

    @property
    def docs(self) -> Path:
        return self.root / "docs"

    @property
    def raw(self) -> Path:
        return self.root / "raw"

    @property
    def extracted(self) -> Path:
        return self.root / "extracted"

    @property
    def proposals(self) -> Path:
        return self.root / "proposals"

    @property
    def wiki(self) -> Path:
        return self.root / "wiki"

    @property
    def read_models(self) -> Path:
        return self.root / "read_models"

    @property
    def registry_dir(self) -> Path:
        return self.root / "data" / "registry"

    @property
    def registry_db(self) -> Path:
        return self.registry_dir / "curiosity.sqlite"

    @property
    def prompts(self) -> Path:
        return self.root / "prompts"

    @property
    def eval(self) -> Path:
        return self.root / "eval"

    @property
    def tests_fixtures(self) -> Path:
        return self.root / "tests" / "fixtures"

    @property
    def ops_logs(self) -> Path:
        return self.root / "docs" / "_ops"

    def all_named(self) -> dict[str, Path]:
        """Alle Pfade als dict — nützlich für CLI-Anzeige und Tests."""
        return {
            "root": self.root,
            "docs": self.docs,
            "raw": self.raw,
            "extracted": self.extracted,
            "proposals": self.proposals,
            "wiki": self.wiki,
            "read_models": self.read_models,
            "registry_dir": self.registry_dir,
            "registry_db": self.registry_db,
            "prompts": self.prompts,
            "eval": self.eval,
            "tests_fixtures": self.tests_fixtures,
            "ops_logs": self.ops_logs,
        }


def get_paths() -> VaultPaths:
    """Default-Factory für VaultPaths."""
    return VaultPaths(root=get_vault_root())
