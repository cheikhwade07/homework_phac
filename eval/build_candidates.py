"""Build the candidate cases to label for each evaluation request (DESIGN D6).

A random sample alone would contain almost no positives for rare concepts (only 40
of 110,182 cases mention a scooter at all), so each test set mixes three strata:

- keyword:       likely positives found by keyword search
- hard_negative: similar-looking cases that should be NO (other vehicles, cardiac
                 terms used in passing)
- random:        a random draw from the rest of the corpus

Writes eval/testsets/<request>.candidates.csv with columns case_id, stratum.
The stratum is hidden from the labeler.

Usage: python eval/build_candidates.py
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

from casefilter.data import load_cases

OUT_DIR = Path(__file__).parent / "testsets"
SEED = 42

CARDIO_CORE = (
    r"myocardial infarction|heart failure|cardiomyopathy|aortic dissection|endocarditis"
    r"|atrial fibrillation|coronary artery disease|STEMI"
)
CARDIO_PASSING = r"hypertension|\bECG\b|electrocardiogra|echocardiogra|chest pain|troponin"

STRATA: dict[str, list[tuple[str, str, str | None, int | None]]] = {
    # (stratum, include pattern, exclude pattern, n or None for all matches)
    "cardio": [
        ("keyword", CARDIO_CORE, None, 15),
        ("hard_negative", CARDIO_PASSING, CARDIO_CORE, 10),
        ("random", r"", None, 15),
    ],
    "escooter": [
        ("keyword", r"scooter", None, None),
        ("hard_negative", r"bicycle|\bbike\b", r"scooter", 4),
        ("hard_negative", r"motorcycl|motorbike", r"scooter", 4),
        ("hard_negative", r"segway|hoverboard|e-?bike|unicycle", r"scooter", 4),
        ("random", r"", None, 8),
    ],
}


def matches(texts: pd.Series, pattern: str) -> pd.Series:
    return texts.str.contains(pattern, flags=re.IGNORECASE, regex=True)


def build(cases: pd.DataFrame, request_id: str) -> pd.DataFrame:
    chosen: list[pd.DataFrame] = []
    taken: set[str] = set()
    for stratum, include, exclude, n in STRATA[request_id]:
        pool = cases[~cases["case_id"].isin(taken)]
        if include:
            pool = pool[matches(pool["case_text"], include)]
        if exclude:
            pool = pool[~matches(pool["case_text"], exclude)]
        if n is not None:
            pool = pool.sample(n=min(n, len(pool)), random_state=SEED)
        picked = pool[["case_id"]].assign(stratum=stratum)
        chosen.append(picked)
        taken.update(picked["case_id"])
    return pd.concat(chosen, ignore_index=True)


def main() -> None:
    cases = load_cases()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for request_id in STRATA:
        candidates = build(cases, request_id)
        candidates.to_csv(OUT_DIR / f"{request_id}.candidates.csv", index=False)
        print(request_id, candidates["stratum"].value_counts().to_dict())


if __name__ == "__main__":
    main()
