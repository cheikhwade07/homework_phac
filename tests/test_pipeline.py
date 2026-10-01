import pandas as pd

from casefilter.pipeline import build_classifier, run_filter, select_cases
from tests.conftest import FakeLLM

FRAME = pd.DataFrame(
    {
        "case_id": [f"C{i}" for i in range(6)],
        "article_id": ["A"] * 6,
        "case_text": ["fell from an e-scooter", "Scooter crash", "flu", "cough", "rash", "burn"],
        "age": [30.0, None, 5.0, 6.0, 7.0, 8.0],
        "gender": ["Male", None, "Female", "Male", "Female", "Male"],
    }
)


def test_keyword_prefilter_is_case_insensitive_and_literal():
    assert {c.case_id for c in select_cases(FRAME, 10, keyword="scooter")} == {"C0", "C1"}
    assert select_cases(FRAME, 10, keyword="e-scooter (") == []


def test_sample_size_and_seed():
    first = select_cases(FRAME, 3, seed=1)
    assert len(first) == 3 and first == select_cases(FRAME, 3, seed=1)
    assert len(select_cases(FRAME, 100)) == 6


def test_run_filter_pairs_each_case_with_its_result():
    cases = select_cases(FRAME, 10, keyword="scooter")
    llm = FakeLLM(['{"label": "YES"}', '{"label": "NO"}'])
    results = run_filter("scooters", cases, build_classifier("classify.v1", llm), max_workers=1)
    assert [(c.case_id, p.case_id) for c, p in results] == [("C0", "C0"), ("C1", "C1")]
    assert [p.label for _, p in results] == ["YES", "NO"]
