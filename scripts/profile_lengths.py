"""Profile case_text length in tokens to decide how long narratives are handled (DESIGN D5).

Tokens are counted exactly with the Gemini tokenizer on a random sample, which
gives a characters-per-token ratio. That ratio is applied to the character
length of every case to estimate the token distribution of the full corpus.

Usage: python scripts/profile_lengths.py [--sample 200]
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import numpy as np
from dotenv import load_dotenv
from google import genai

from casefilter.data import load_cases

OUT = Path("eval/results/length_profile.json")
LIMITS = {"llm_context": 1_048_576, "embedding_input": 8_192}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample", type=int, default=200)
    args = parser.parse_args()

    load_dotenv()
    model = os.getenv("CASEFILTER_MODEL", "gemini-2.5-flash")
    client = genai.Client()

    cases = load_cases()
    sample = cases.sample(n=args.sample, random_state=0)
    tokens = np.array(
        [
            client.models.count_tokens(model=model, contents=text).total_tokens
            for text in sample["case_text"]
        ]
    )
    chars_per_token = float(sample["case_text"].str.len().sum() / tokens.sum())
    est_tokens = cases["case_text"].str.len() / chars_per_token

    percentiles = [50, 90, 99, 99.9, 100]
    profile = {
        "model_tokenizer": model,
        "n_cases": int(len(cases)),
        "sample_size": int(args.sample),
        "chars_per_token": round(chars_per_token, 2),
        "estimated_tokens_percentiles": {
            f"p{p}": int(np.percentile(est_tokens, p)) for p in percentiles
        },
        "share_over_limit": {
            name: round(float((est_tokens > limit).mean()), 5) for name, limit in LIMITS.items()
        },
        "cases_over_limit": {
            name: int((est_tokens > limit).sum()) for name, limit in LIMITS.items()
        },
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(profile, indent=2) + "\n")
    print(json.dumps(profile, indent=2))


if __name__ == "__main__":
    main()
