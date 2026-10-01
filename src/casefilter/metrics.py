"""Binary classification metrics with YES as the positive class."""

from __future__ import annotations

from collections.abc import Sequence


def confusion(reference: Sequence[str], predicted: Sequence[str]) -> dict[str, int]:
    """Count TP/FP/FN/TN. A prediction that is not YES (NO or ERROR) counts as negative."""
    if len(reference) != len(predicted):
        raise ValueError("reference and predicted must have the same length")
    counts = {"tp": 0, "fp": 0, "fn": 0, "tn": 0}
    for truth, guess in zip(reference, predicted, strict=True):
        positive = guess == "YES"
        if truth == "YES":
            counts["tp" if positive else "fn"] += 1
        else:
            counts["fp" if positive else "tn"] += 1
    return counts


def scores(reference: Sequence[str], predicted: Sequence[str]) -> dict[str, float | int | None]:
    """Precision, recall, F1 and accuracy. A metric is None when its denominator is zero."""
    c = confusion(reference, predicted)
    tp, fp, fn, tn = c["tp"], c["fp"], c["fn"], c["tn"]
    precision = tp / (tp + fp) if tp + fp else None
    recall = tp / (tp + fn) if tp + fn else None
    if precision is None or recall is None or precision + recall == 0:
        f1 = None
    else:
        f1 = 2 * precision * recall / (precision + recall)
    total = tp + fp + fn + tn
    return {
        "n": total,
        **c,
        "precision": _round(precision),
        "recall": _round(recall),
        "f1": _round(f1),
        "accuracy": _round((tp + tn) / total if total else None),
    }


def _round(value: float | None) -> float | None:
    return None if value is None else round(value, 3)
