"""Criterion expansion: rewrite a user's request as an explicit definition.

One LLM call per request, made before any case is classified. Every case is then
judged against the same definition, which keeps decisions consistent across cases
and makes the interpretation of the request visible to the user.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from casefilter.llm import LLMClient
from casefilter.prompts import PromptTemplate, load_prompt

DEFAULT_EXPANSION_PROMPT = "expand.v1"


@dataclass(frozen=True)
class CriterionDefinition:
    request: str
    concept: str
    includes: tuple[str, ...] = ()
    excludes: tuple[str, ...] = ()

    def to_text(self) -> str:
        lines = [f"Concept: {self.concept}"]
        if self.includes:
            lines.append("Counts as the concept: " + "; ".join(self.includes))
        if self.excludes:
            lines.append("Does not count: " + "; ".join(self.excludes))
        return "\n".join(lines)


def expand_criterion(
    client: LLMClient, request: str, prompt: PromptTemplate | None = None
) -> CriterionDefinition:
    """Ask the LLM to define the requested concept. Raises ValueError on unusable output."""
    prompt = prompt or load_prompt(DEFAULT_EXPANSION_PROMPT)
    system, user = prompt.render(classification_criteria=request)
    response = client.generate_json(system, user, prompt.schema)
    try:
        data = json.loads(response.text)
        concept = str(data["concept"]).strip()
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        raise ValueError(f"unusable criterion expansion: {response.text[:80]!r}") from exc
    if not concept:
        raise ValueError("criterion expansion returned an empty concept")
    return CriterionDefinition(
        request=request,
        concept=concept,
        includes=tuple(str(item).strip() for item in data.get("includes") or []),
        excludes=tuple(str(item).strip() for item in data.get("excludes") or []),
    )
