import pytest

from casefilter.classifier import LLMClassifier
from casefilter.expansion import expand_criterion
from casefilter.prompts import load_prompt
from tests.conftest import FakeLLM

EXPANSION = (
    '{"concept": "Injury while riding an electric scooter.", '
    '"includes": ["e-scooter crash"], "excludes": ["moped injury"]}'
)
VERDICT = '{"reason": "r", "label": "NO", "evidence": ""}'


def test_expansion_is_parsed_and_rendered():
    definition = expand_criterion(FakeLLM([EXPANSION]), "e-scooter injuries")
    assert definition.includes == ("e-scooter crash",)
    assert definition.excludes == ("moped injury",)
    text = definition.to_text()
    assert text.startswith("Concept: Injury while riding an electric scooter.")
    assert "Counts as the concept: e-scooter crash" in text
    assert "Does not count: moped injury" in text


@pytest.mark.parametrize("bad", ["not json", "{}", '{"concept": "  "}'])
def test_unusable_expansion_is_rejected(bad):
    with pytest.raises(ValueError):
        expand_criterion(FakeLLM([bad]), "anything")


def test_request_is_expanded_once_and_reused_for_every_case(case):
    llm = FakeLLM([EXPANSION, VERDICT, VERDICT])
    classifier = LLMClassifier(llm, load_prompt("classify.v3"))
    classifier.classify("e-scooter injuries", case)
    classifier.classify("e-scooter injuries", case)
    assert len(llm.calls) == 3
    for _, user, _ in llm.calls[1:]:
        assert "Concept: Injury while riding an electric scooter." in user
        assert "Does not count: moped injury" in user


def test_failed_expansion_gives_error_not_no(case):
    classifier = LLMClassifier(FakeLLM(["not json"]), load_prompt("classify.v3"))
    assert classifier.classify("x", case).label == "ERROR"


def test_prompts_without_a_definition_skip_the_expansion(case):
    llm = FakeLLM(['{"label": "YES"}'])
    classifier = LLMClassifier(llm, load_prompt("classify.v1"))
    assert classifier.definition_for("x") is None
    classifier.classify("x", case)
    assert len(llm.calls) == 1
