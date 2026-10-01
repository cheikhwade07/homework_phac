"""Label evaluation cases by hand in the terminal, blind to model output.

Cases are shown in a shuffled order without their sampling stratum. Answers are
saved after every case, so labeling can stop and resume at any time.

Keys:  y = YES   n = NO   y? / n? = YES / NO, flagged ambiguous (asks for a note)
       s = skip for now   q = save and quit

Usage: python eval/label.py cardio
       python eval/label.py escooter
"""

from __future__ import annotations

import random
import shutil
import sys
import textwrap
import tomllib
from pathlib import Path

import pandas as pd

from casefilter.data import get_cases, load_cases

EVAL_DIR = Path(__file__).parent
COLUMNS = ["case_id", "human_label", "ambiguous", "note"]


def main(request_id: str) -> None:
    requests = tomllib.loads((EVAL_DIR / "requests.toml").read_text())
    request = requests[request_id]["text"]
    candidates = pd.read_csv(EVAL_DIR / "testsets" / f"{request_id}.candidates.csv")
    labels_path = EVAL_DIR / "testsets" / f"{request_id}.labels.csv"
    labels = (
        pd.read_csv(labels_path, keep_default_na=False)
        if labels_path.exists()
        else pd.DataFrame(columns=COLUMNS)
    )

    order = list(candidates["case_id"])
    random.Random(0).shuffle(order)
    todo = [cid for cid in order if cid not in set(labels["case_id"])]
    cases = {c.case_id: c for c in get_cases(load_cases(), todo)}
    width = min(100, shutil.get_terminal_size().columns - 2)

    for done, case_id in enumerate(todo, start=len(labels) + 1):
        print("\n" + "=" * width)
        print(f"[{done}/{len(order)}]  {request}   (rules: eval/guidelines.md)")
        print("=" * width)
        for paragraph in cases[case_id].case_text.split("\n"):
            print(textwrap.fill(paragraph, width) if paragraph.strip() else "")
        while True:
            answer = input("\nRelevant? [y / n / y? / n? / s / q] ").strip().lower()
            if answer in {"y", "n", "y?", "n?", "s", "q"}:
                break
        if answer == "q":
            break
        if answer == "s":
            continue
        ambiguous = answer.endswith("?")
        note = input("Note (why ambiguous): ").strip() if ambiguous else ""
        row = {
            "case_id": case_id,
            "human_label": "YES" if answer.startswith("y") else "NO",
            "ambiguous": int(ambiguous),
            "note": note,
        }
        labels = pd.concat([labels, pd.DataFrame([row])], ignore_index=True)
        labels.to_csv(labels_path, index=False)

    print(f"\nSaved {len(labels)}/{len(order)} labels to {labels_path}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
