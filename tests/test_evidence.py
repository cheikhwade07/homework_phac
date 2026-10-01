import pytest

from casefilter.classifier import LLMClassifier, evidence_in_text
from casefilter.prompts import load_prompt
from tests.conftest import FakeLLM

TEXT = "A 24-year-old patient was admitted following a collision\nwhile riding an electric scooter."


@pytest.mark.parametrize(
    "quote",
    [
        "riding an electric scooter",
        "Collision while  riding an ELECTRIC scooter.",
        '"admitted following a collision"',
        "A 24-year-old patient ... electric scooter",
    ],
)
def test_real_quotes_are_found(quote):
    assert evidence_in_text(quote, TEXT)


@pytest.mark.parametrize("quote", ["riding a motorcycle", "", None, "patient ... motorcycle"])
def test_invented_or_empty_quotes_are_not_found(quote):
    assert not evidence_in_text(quote, TEXT)


def test_v2_flags_a_quote_that_is_not_in_the_case(case):
    llm = FakeLLM(['{"evidence": "acute leukemia", "reason": "r", "label": "YES"}'])
    prediction = LLMClassifier(llm, load_prompt("classify.v2")).classify("leukemia", case)
    assert prediction.label == "YES" and prediction.evidence_found is False


def test_v2_verifies_a_real_quote(case):
    llm = FakeLLM(['{"evidence": "chest pain", "reason": "r", "label": "YES"}'])
    prediction = LLMClassifier(llm, load_prompt("classify.v2")).classify("chest pain", case)
    assert prediction.evidence_found is True


def test_no_label_has_no_evidence_check(case):
    llm = FakeLLM(['{"evidence": "", "reason": "r", "label": "NO"}'])
    prediction = LLMClassifier(llm, load_prompt("classify.v2")).classify("leukemia", case)
    assert prediction.label == "NO" and prediction.evidence_found is None


def test_v2_keeps_request_and_case_in_separate_tags(case):
    llm = FakeLLM(['{"evidence": "", "reason": "r", "label": "NO"}'])
    LLMClassifier(llm, load_prompt("classify.v2")).classify("my request", case)
    system, user, _ = llm.calls[0]
    assert "<request>\nmy request\n</request>" in user
    assert f"<case>\n{case.case_text}\n</case>" in user
    assert "my request" not in system
