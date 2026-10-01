"""Versioned prompt templates stored as TOML files in ``prompts/``.

Each file holds the system instruction, the user message template and the JSON
schema of the expected output, so a prompt and its output contract change
together under one version name.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PROMPTS_DIR = Path(__file__).resolve().parents[2] / "prompts"


@dataclass(frozen=True)
class PromptTemplate:
    version: str
    description: str
    system: str
    user: str
    schema: dict[str, Any]

    def render(self, **values: str) -> tuple[str, str]:
        """Fill the placeholders and return ``(system, user)`` messages.

        Values are inserted verbatim, so braces inside a case text are safe.
        Raises KeyError if a placeholder has no value.
        """
        return self.system.format_map(values), self.user.format_map(values)


def load_prompt(version: str, directory: Path = PROMPTS_DIR) -> PromptTemplate:
    """Load ``<directory>/<version>.toml``, for example ``load_prompt("classify.v1")``."""
    path = directory / f"{version}.toml"
    with path.open("rb") as handle:
        data = tomllib.load(handle)
    if data.get("version") != version:
        raise ValueError(f"{path.name} declares version {data.get('version')!r}")
    return PromptTemplate(
        version=data["version"],
        description=data.get("description", ""),
        system=data.get("system", "").strip(),
        user=data["user"].strip(),
        schema=data["schema"],
    )
