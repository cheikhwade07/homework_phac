"""Load the MultiCaRe dataset and flatten it to one row per clinical case.

The Hugging Face dataset has one row per article, each holding a nested list of
cases. Classification works on individual cases, so the articles are exploded
into a flat table keyed by ``case_id`` and cached locally as Parquet.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

DATASET_NAME = "OpenMed/multicare-cases"
DEFAULT_CACHE = Path("data/cases.parquet")
COLUMNS = ["case_id", "article_id", "case_text", "age", "gender"]


@dataclass(frozen=True)
class Case:
    case_id: str
    article_id: str
    case_text: str
    age: int | None = None
    gender: str | None = None


def flatten_articles(articles: pd.DataFrame) -> pd.DataFrame:
    """Turn article rows with a nested ``cases`` list into one row per case."""
    exploded = articles[["article_id", "cases"]].explode("cases", ignore_index=True)
    exploded = exploded.dropna(subset=["cases"])
    nested = pd.json_normalize(exploded["cases"].tolist())
    flat = pd.concat([exploded[["article_id"]].reset_index(drop=True), nested], axis=1)
    flat = flat.dropna(subset=["case_text"])
    flat = flat[flat["case_text"].str.strip() != ""]
    flat = flat.drop_duplicates(subset="case_id")
    return flat[COLUMNS].reset_index(drop=True)


def load_cases(cache_path: Path = DEFAULT_CACHE) -> pd.DataFrame:
    """Return all cases as a flat DataFrame, downloading and caching on first use."""
    if cache_path.exists():
        return pd.read_parquet(cache_path)

    from datasets import load_dataset

    articles = load_dataset(DATASET_NAME, split="train").to_pandas()
    cases = flatten_articles(articles)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cases.to_parquet(cache_path, index=False)
    return cases


def to_cases(frame: pd.DataFrame) -> list[Case]:
    """Convert rows of a case DataFrame to ``Case`` objects."""
    return [
        Case(
            case_id=row.case_id,
            article_id=row.article_id,
            case_text=row.case_text,
            age=None if pd.isna(row.age) else int(row.age),
            gender=None if pd.isna(row.gender) else str(row.gender),
        )
        for row in frame.itertuples(index=False)
    ]


def sample_cases(frame: pd.DataFrame, n: int, seed: int = 42) -> list[Case]:
    """Draw a reproducible random sample of ``n`` cases."""
    n = min(n, len(frame))
    return to_cases(frame.sample(n=n, random_state=seed))


def get_cases(frame: pd.DataFrame, case_ids: list[str]) -> list[Case]:
    """Return cases in the order of ``case_ids``. Raises KeyError for unknown IDs."""
    indexed = frame.set_index("case_id", drop=False)
    missing = [cid for cid in case_ids if cid not in indexed.index]
    if missing:
        raise KeyError(f"Unknown case_id(s): {missing[:5]}")
    return to_cases(indexed.loc[case_ids])
