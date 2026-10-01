import pytest

from casefilter.classifier import LLMClassifier, classify_many, parse_output
from casefilter.data import Case
from casefilter.prompts import load_prompt
from tests.conftest import FakeLLM


@pytest.mark.parametrize(
    ("text", "label"),
    [
        ('{"label": "YES"}', "YES"),
        ('{"label": "no"}', "NO"),
        ("YES", "YES"),
        ("  no.", "NO"),
    ],
)
def test_parse_accepts_valid_labels(text, label):
    assert parse_output(text)["label"] == label


@pytest.mark.parametrize(
    "text", ['{"label": "MAYBE"}', '["YES"]', "", "The answer is yes", "NOT SURE"]
)
def test_parse_rejects_invalid_output(text):
    with pytest.raises(ValueError):
        parse_output(text)


def test_parse_keeps_evidence_and_reason():
    parsed = parse_output('{"label": "YES", "evidence": "chest pain", "reason": "r"}')
    assert parsed == {"label": "YES", "evidence": "chest pain", "reason": "r"}


def test_classifier_sends_criterion_and_case(case):
    llm = FakeLLM(['{"label": "YES"}'])
    prediction = LLMClassifier(llm, load_prompt("classify.v1")).classify("cardiac", case)
    _, user, schema = llm.calls[0]
    assert prediction.label == "YES" and prediction.case_id == "C1"
    assert "cardiac" in user and case.case_text in user
    assert schema["properties"]["label"]["enum"] == ["YES", "NO"]


def test_bad_output_becomes_error_not_no(case):
    prediction = LLMClassifier(FakeLLM(["garbage"]), load_prompt("classify.v1")).classify(
        "cardiac", case
    )
    assert prediction.label == "ERROR" and prediction.error


def test_provider_failure_becomes_error(case):
    class Failing:
        model = "fake"

        def generate_json(self, *args):
            raise RuntimeError("quota exceeded")

    prediction = LLMClassifier(Failing(), load_prompt("classify.v1")).classify("x", case)
    assert prediction.label == "ERROR" and "quota" in prediction.error


def test_classify_many_preserves_order():
    cases = [Case(f"C{i}", "A", f"text {i}") for i in range(5)]

    class EchoParity:
        name = "parity"

        def classify(self, criterion, case):
            from casefilter.classifier import Prediction

            return Prediction(case.case_id, "YES" if int(case.case_id[1:]) % 2 else "NO", "p")

    predictions = classify_many(EchoParity(), "x", cases, max_workers=3)
    assert [p.case_id for p in predictions] == [c.case_id for c in cases]
    assert [p.label for p in predictions] == ["NO", "YES", "NO", "YES", "NO"]
