"""Evaluate two embedding-based classifiers on the same labeled sets as the LLM.

1. similarity: cosine similarity between the request and the case, YES above a
   threshold. Needs no training examples, only a threshold.
2. logreg: logistic regression trained on case embeddings with their labels. Needs
   labeled examples for every new request.

Both are scored with leave-one-out cross-validation: each case is predicted by a
threshold or model fitted on all the other cases, so no case is scored by something
that saw its own label.

Writes eval/results/<request>.embedding.metrics.json and .predictions.csv

Usage: python eval/run_embedding_eval.py cardio
"""

from __future__ import annotations

import argparse
import json
import tomllib
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression

from casefilter.data import get_cases, load_cases
from casefilter.embedding import GeminiEmbedder
from casefilter.metrics import scores

EVAL_DIR = Path(__file__).parent


def best_threshold(similarity: np.ndarray, positive: np.ndarray) -> float:
    """Threshold with the highest F1 on the given cases (midpoints between sorted scores)."""
    ordered = np.sort(np.unique(similarity))
    candidates = (ordered[:-1] + ordered[1:]) / 2 if len(ordered) > 1 else ordered
    best, best_f1 = float(candidates[0]), -1.0
    for threshold in candidates:
        predicted = similarity >= threshold
        tp = int((predicted & positive).sum())
        f1 = 2 * tp / (predicted.sum() + positive.sum()) if tp else 0.0
        if f1 > best_f1:
            best, best_f1 = float(threshold), f1
    return best


def leave_one_out(n: int):
    for held_out in range(n):
        yield np.array([i for i in range(n) if i != held_out]), held_out


def evaluate(request_id: str) -> dict:
    request = tomllib.loads((EVAL_DIR / "requests.toml").read_text())[request_id]["text"]
    labels = pd.read_csv(EVAL_DIR / "testsets" / f"{request_id}.labels.csv", keep_default_na=False)
    cases = get_cases(load_cases(), list(labels["case_id"]))
    reference = list(labels["reference_label"])
    positive = np.array([label == "YES" for label in reference])

    embedder = GeminiEmbedder()
    vectors = np.vstack([embedder.embed(case.case_text) for case in cases])
    case_seconds, case_calls = embedder.seconds_spent, embedder.api_calls
    similarity = vectors @ embedder.embed(request)

    sim_pred, logreg_pred = [], []
    for train, held_out in leave_one_out(len(cases)):
        threshold = best_threshold(similarity[train], positive[train])
        sim_pred.append("YES" if similarity[held_out] >= threshold else "NO")
        model = LogisticRegression(class_weight="balanced", max_iter=1000)
        model.fit(vectors[train], positive[train])
        logreg_pred.append("YES" if model.predict(vectors[[held_out]])[0] else "NO")

    metrics = {
        "request_id": request_id,
        "request": request,
        "embedding_model": embedder.model,
        "dimensions": int(vectors.shape[1]),
        "validation": "leave-one-out",
        "similarity": scores(reference, sim_pred),
        "logreg": scores(reference, logreg_pred),
        "similarity_threshold_all_cases": round(best_threshold(similarity, positive), 4),
        "mean_embedding_latency_s": round(case_seconds / case_calls, 2) if case_calls else None,
    }
    stem = EVAL_DIR / "results" / f"{request_id}.embedding"
    Path(f"{stem}.metrics.json").write_text(json.dumps(metrics, indent=2) + "\n")
    labels.assign(
        similarity=similarity.round(4), similarity_predicted=sim_pred, logreg_predicted=logreg_pred
    )[
        ["case_id", "reference_label", "ambiguous", "similarity", "similarity_predicted",
         "logreg_predicted"]
    ].to_csv(f"{stem}.predictions.csv", index=False)
    return metrics


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("request_id")
    print(json.dumps(evaluate(parser.parse_args().request_id), indent=2))


if __name__ == "__main__":
    main()
