import pytest

from casefilter.metrics import confusion, scores


def test_confusion_counts():
    human = ["YES", "YES", "NO", "NO", "YES"]
    predicted = ["YES", "NO", "YES", "NO", "ERROR"]
    assert confusion(human, predicted) == {"tp": 1, "fp": 1, "fn": 2, "tn": 1}


def test_scores_match_hand_calculation():
    human = ["YES"] * 4 + ["NO"] * 6
    predicted = ["YES", "YES", "YES", "NO"] + ["YES"] + ["NO"] * 5
    result = scores(human, predicted)
    assert (result["tp"], result["fp"], result["fn"], result["tn"]) == (3, 1, 1, 5)
    assert result["precision"] == 0.75 and result["recall"] == 0.75
    assert result["f1"] == 0.75 and result["accuracy"] == 0.8


def test_undefined_metrics_are_none():
    result = scores(["NO", "NO"], ["NO", "NO"])
    assert result["precision"] is None and result["recall"] is None and result["f1"] is None


def test_length_mismatch_is_rejected():
    with pytest.raises(ValueError):
        confusion(["YES"], [])
