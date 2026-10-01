"""Relevance classifiers: decide whether a case matches a user's criterion.

Every classifier implements the ``Classifier`` protocol, so the evaluation
runner and the user interface work with LLM and embedding approaches alike.
"""

from __future__ import annotations

import json
import re
import threading
from collections.abc import Callable, Iterable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Literal, Protocol

from casefilter.data import Case
from casefilter.expansion import CriterionDefinition, expand_criterion
from casefilter.llm import LLMClient
from casefilter.prompts import PromptTemplate

Label = Literal["YES", "NO", "ERROR"]
_BARE_LABEL = re.compile(r"^\W*(YES|NO)\b", re.IGNORECASE)
_ELLIPSIS = re.compile(r"\.{3,}|…")


@dataclass(frozen=True)
class Prediction:
    case_id: str
    label: Label
    method: str
    evidence: str | None = None
    reason: str | None = None
    evidence_found: bool | None = None
    latency_s: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    cached: bool = False
    error: str | None = None


class Classifier(Protocol):
    name: str

    def classify(self, criterion: str, case: Case) -> Prediction: ...


def parse_output(text: str) -> dict[str, str | None]:
    """Extract ``label`` (and optional ``evidence``/``reason``) from a model response.

    Accepts the expected JSON object, and falls back to a bare YES/NO answer.
    Raises ValueError for anything else, so bad output is never read as NO.
    """
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        match = _BARE_LABEL.match(text or "")
        if not match:
            raise ValueError(f"unparseable model output: {text[:80]!r}") from None
        return {"label": match.group(1).upper(), "evidence": None, "reason": None}

    if not isinstance(data, dict):
        raise ValueError(f"expected a JSON object, got {type(data).__name__}")
    label = str(data.get("label", "")).strip().upper()
    if label not in {"YES", "NO"}:
        raise ValueError(f"invalid label: {data.get('label')!r}")
    return {"label": label, "evidence": data.get("evidence"), "reason": data.get("reason")}


def _normalise(text: str) -> str:
    return " ".join(text.replace("’", "'").split()).casefold().strip(" \"'.")


def evidence_in_text(evidence: str | None, case_text: str) -> bool:
    """Check that a quoted evidence string really appears in the case text.

    Models can produce quotes that are not in the source. Whitespace, case and
    surrounding quotation marks are ignored, and a quote joined with an ellipsis
    passes only if every part is present.
    """
    if not evidence or not evidence.strip():
        return False
    haystack = _normalise(case_text)
    parts = [_normalise(part) for part in _ELLIPSIS.split(evidence)]
    parts = [part for part in parts if part]
    return bool(parts) and all(part in haystack for part in parts)


class LLMClassifier:
    """One LLM call per (criterion, case) pair using a versioned prompt template."""

    def __init__(self, client: LLMClient, prompt: PromptTemplate):
        self.client = client
        self.prompt = prompt
        self.name = f"llm:{client.model}:{prompt.version}"
        self.uses_definition = "{criterion_definition}" in prompt.system + prompt.user
        self._definitions: dict[str, CriterionDefinition] = {}
        self._lock = threading.Lock()

    def definition_for(self, criterion: str) -> CriterionDefinition | None:
        """Expand the request once and reuse the definition for every case."""
        if not self.uses_definition:
            return None
        with self._lock:
            if criterion not in self._definitions:
                self._definitions[criterion] = expand_criterion(self.client, criterion)
            return self._definitions[criterion]

    def classify(self, criterion: str, case: Case) -> Prediction:
        try:
            definition = self.definition_for(criterion)
            system, user = self.prompt.render(
                classification_criteria=criterion,
                criterion_definition=definition.to_text() if definition else "",
                case_text=case.case_text,
            )
            response = self.client.generate_json(system, user, self.prompt.schema)
        except Exception as exc:  # provider failure after the client's own retries
            return Prediction(case.case_id, "ERROR", self.name, error=f"llm call: {exc}")

        usage = {
            "latency_s": response.latency_s,
            "input_tokens": response.input_tokens,
            "output_tokens": response.output_tokens,
            "cached": response.cached,
        }
        try:
            parsed = parse_output(response.text)
        except ValueError as exc:
            return Prediction(case.case_id, "ERROR", self.name, error=str(exc), **usage)
        asks_for_evidence = "evidence" in self.prompt.schema.get("properties", {})
        evidence_found = (
            evidence_in_text(parsed["evidence"], case.case_text)
            if asks_for_evidence and parsed["label"] == "YES"
            else None
        )
        return Prediction(
            case.case_id,
            parsed["label"],
            self.name,
            evidence=parsed["evidence"] or None,
            reason=parsed["reason"],
            evidence_found=evidence_found,
            **usage,
        )


def classify_many(
    classifier: Classifier,
    criterion: str,
    cases: Iterable[Case],
    max_workers: int = 4,
    on_result: Callable[[Prediction], None] | None = None,
) -> list[Prediction]:
    """Classify cases concurrently and return predictions in input order."""
    cases = list(cases)

    def run(case: Case) -> Prediction:
        prediction = classifier.classify(criterion, case)
        if on_result is not None:
            on_result(prediction)
        return prediction

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        return list(pool.map(run, cases))
