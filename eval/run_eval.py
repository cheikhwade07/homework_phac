"""Compare the classifier with the reference labels for one evaluation request.

Reads   eval/testsets/<request>.labels.csv  and  <request>.candidates.csv
Writes  eval/results/<request>.<prompt>.metrics.json
        eval/results/<request>.<prompt>.predictions.csv   (one row per case)

Usage: python eval/run_eval.py cardio --prompt classify.v2
"""

from __future__ import annotations

import argparse
import json
import tomllib
from pathlib import Path

import pandas as pd

from casefilter.data import get_cases, load_cases
from casefilter.metrics import scores
from casefilter.pipeline import DEFAULT_PROMPT, build_classifier, run_filter

EVAL_DIR = Path(__file__).parent


def evaluate(request_id: str, prompt_version: str) -> dict:
    request = tomllib.loads((EVAL_DIR / "requests.toml").read_text())[request_id]["text"]
    labels = pd.read_csv(EVAL_DIR / "testsets" / f"{request_id}.labels.csv", keep_default_na=False)
    strata = pd.read_csv(EVAL_DIR / "testsets" / f"{request_id}.candidates.csv")
    labels = labels.rename(columns={"evidence": "reference_evidence", "note": "reference_note"})
    labels = labels.merge(strata, on="case_id", how="left")

    classifier = build_classifier(prompt_version)
    cases = get_cases(load_cases(), list(labels["case_id"]))
    results = run_filter(request, cases, classifier)
    predictions = [prediction for _, prediction in results]

    table = labels.assign(
        predicted=[p.label for p in predictions],
        evidence=[p.evidence or "" for p in predictions],
        evidence_found=[p.evidence_found for p in predictions],
        reason=[p.reason or "" for p in predictions],
        error=[p.error or "" for p in predictions],
    )
    table["outcome"] = [
        _outcome(h, p) for h, p in zip(table["reference_label"], table["predicted"], strict=True)
    ]

    clear = table[table["ambiguous"].astype(int) == 0]
    fresh = [p for p in predictions if not p.cached and p.label != "ERROR"]
    yes = [p for p in predictions if p.label == "YES" and p.evidence_found is not None]
    metrics = {
        "request_id": request_id,
        "request": request,
        "classifier": classifier.name,
        "all_cases": scores(list(table["reference_label"]), list(table["predicted"])),
        "excluding_ambiguous": scores(list(clear["reference_label"]), list(clear["predicted"])),
        "by_stratum": {
            name: scores(list(group["reference_label"]), list(group["predicted"]))
            for name, group in table.groupby("stratum")
        },
        "errors": int((table["predicted"] == "ERROR").sum()),
        "evidence_not_found": sum(1 for p in yes if p.evidence_found is False),
        "evidence_checked": len(yes),
        "mean_latency_s": round(sum(p.latency_s for p in fresh) / len(fresh), 2) if fresh else None,
        "mean_input_tokens": round(sum(p.input_tokens for p in predictions) / len(predictions)),
        "mean_output_tokens": round(sum(p.output_tokens for p in predictions) / len(predictions)),
        "false_positives": list(table.loc[table["outcome"] == "FP", "case_id"]),
        "false_negatives": list(table.loc[table["outcome"] == "FN", "case_id"]),
    }

    stem = EVAL_DIR / "results" / f"{request_id}.{prompt_version}"
    stem.parent.mkdir(parents=True, exist_ok=True)
    Path(f"{stem}.metrics.json").write_text(json.dumps(metrics, indent=2) + "\n")
    table.to_csv(f"{stem}.predictions.csv", index=False)
    return metrics


def _outcome(reference: str, predicted: str) -> str:
    if reference == "YES":
        return "TP" if predicted == "YES" else "FN"
    return "FP" if predicted == "YES" else "TN"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("request_id")
    parser.add_argument("--prompt", default=DEFAULT_PROMPT)
    args = parser.parse_args()
    metrics = evaluate(args.request_id, args.prompt)
    summary = {k: metrics[k] for k in ("classifier", "all_cases", "excluding_ambiguous", "errors")}
    print(json.dumps(summary, indent=2))
    print("FP:", metrics["false_positives"])
    print("FN:", metrics["false_negatives"])


if __name__ == "__main__":
    main()
