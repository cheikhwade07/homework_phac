from dataclasses import dataclass, field

import pytest

from casefilter.data import Case
from casefilter.llm import LLMResponse


@dataclass
class FakeLLM:
    """Returns canned responses and records every request."""

    responses: list[str]
    model: str = "fake-model"
    calls: list[tuple[str, str, dict]] = field(default_factory=list)

    def generate_json(self, system, user, schema):
        self.calls.append((system, user, schema))
        return LLMResponse(text=self.responses[len(self.calls) - 1], model=self.model)


@pytest.fixture
def case():
    return Case(case_id="C1", article_id="A1", case_text="Patient with {braces} and chest pain.")
