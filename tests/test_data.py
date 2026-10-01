import pandas as pd
import pytest

from casefilter.data import flatten_articles, get_cases, sample_cases


@pytest.fixture
def articles():
    return pd.DataFrame(
        {
            "article_id": ["A1", "A2", "A3"],
            "cases": [
                [
                    {"case_id": "A1_01", "case_text": "First case.", "age": 50, "gender": "Female"},
                    {"case_id": "A1_02", "case_text": "Second case.", "age": None, "gender": None},
                ],
                [{"case_id": "A2_01", "case_text": "   ", "age": 30, "gender": "Male"}],
                [],
            ],
        }
    )


def test_flatten_gives_one_row_per_case(articles):
    flat = flatten_articles(articles)
    assert list(flat["case_id"]) == ["A1_01", "A1_02"]
    assert list(flat["article_id"]) == ["A1", "A1"]


def test_flatten_drops_blank_text(articles):
    assert "A2_01" not in set(flatten_articles(articles)["case_id"])


def test_missing_metadata_becomes_none(articles):
    cases = get_cases(flatten_articles(articles), ["A1_02"])
    assert cases[0].age is None and cases[0].gender is None


def test_sample_is_reproducible(articles):
    flat = flatten_articles(articles)
    assert sample_cases(flat, 1, seed=1) == sample_cases(flat, 1, seed=1)


def test_get_cases_rejects_unknown_id(articles):
    with pytest.raises(KeyError):
        get_cases(flatten_articles(articles), ["missing"])
