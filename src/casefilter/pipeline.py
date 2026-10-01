"""Shared entry points used by the command-line tool, the web app and the evaluation."""

from __future__ import annotations

import re
from collections.abc import Callable

import pandas as pd

from casefilter.classifier import LLMClassifier, Prediction, classify_many
from casefilter.data import Case, to_cases
from casefilter.llm import GeminiClient, LLMClient
from casefilter.prompts import load_prompt

DEFAULT_PROMPT = "classify.v3"


def select_cases(
    cases: pd.DataFrame, n: int, seed: int = 0, keyword: str | None = None
) -> list[Case]:
    """Pick the cases to classify: a random sample, optionally pre-filtered by keyword.

    The keyword is a case-insensitive literal match on ``case_text``. It is a cheap
    first stage for rare concepts, where a random sample would contain no positives.
    """
    pool = cases
    if keyword and keyword.strip():
        pattern = re.escape(keyword.strip())
        pool = cases[cases["case_text"].str.contains(pattern, case=False, regex=True)]
    if len(pool) > n:
        pool = pool.sample(n=n, random_state=seed)
    return to_cases(pool)


def build_classifier(
    prompt_version: str = DEFAULT_PROMPT, client: LLMClient | None = None
) -> LLMClassifier:
    return LLMClassifier(client or GeminiClient(), load_prompt(prompt_version))


def run_filter(
    request: str,
    cases: list[Case],
    classifier: LLMClassifier | None = None,
    max_workers: int = 4,
    on_result: Callable[[Prediction], None] | None = None,
) -> list[tuple[Case, Prediction]]:
    """Classify every case against the request and pair each case with its prediction."""
    classifier = classifier or build_classifier()
    predictions = classify_many(classifier, request, cases, max_workers, on_result)
    return list(zip(cases, predictions, strict=True))
