"""Text embeddings for the embedding-based comparison (DESIGN D9).

Each text becomes one unit-length vector. Texts longer than the embedding
model's input limit are split into overlapping chunks whose vectors are averaged.
Vectors are cached on disk, so each case is embedded once.
"""

from __future__ import annotations

import os
import random
import time
from pathlib import Path

import numpy as np

from casefilter.llm import RETRYABLE_CODES, ResponseCache

DEFAULT_EMBEDDING_MODEL = "gemini-embedding-2"
DEFAULT_CACHE = Path(".cache/embeddings.sqlite")
# The model accepts 8,192 tokens. At about 4.6 characters per token (see
# eval/results/length_profile.json), 24,000 characters leaves a safe margin.
MAX_CHARS = 24_000
OVERLAP_CHARS = 2_000


def split_long_text(
    text: str, max_chars: int = MAX_CHARS, overlap: int = OVERLAP_CHARS
) -> list[str]:
    """Return the text whole if it fits, otherwise overlapping chunks covering all of it."""
    if len(text) <= max_chars:
        return [text]
    step = max_chars - overlap
    return [text[start : start + max_chars] for start in range(0, len(text) - overlap, step)]


def normalise(vector: np.ndarray) -> np.ndarray:
    norm = np.linalg.norm(vector)
    return vector / norm if norm else vector


class GeminiEmbedder:
    def __init__(self, model: str | None = None, cache: ResponseCache | None = None):
        from dotenv import load_dotenv
        from google import genai

        load_dotenv()
        self.model = model or os.getenv("CASEFILTER_EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL)
        self.cache = cache if cache is not None else ResponseCache(DEFAULT_CACHE)
        self._client = genai.Client()
        self.seconds_spent = 0.0
        self.api_calls = 0

    def embed(self, text: str) -> np.ndarray:
        """Embed one text (chunked and averaged if long) as a unit vector."""
        key = ResponseCache.key(model=self.model, text=text)
        hit = self.cache.get(key)
        if hit is not None:
            return np.array(hit["vector"])
        chunks = [self._embed_chunk(chunk) for chunk in split_long_text(text)]
        vector = normalise(np.mean(chunks, axis=0))
        self.cache.put(key, {"vector": vector.tolist()})
        return vector

    def _embed_chunk(self, text: str, max_retries: int = 6) -> np.ndarray:
        from google.genai import errors

        for attempt in range(max_retries):
            start = time.perf_counter()
            try:
                result = self._client.models.embed_content(model=self.model, contents=[text])
            except errors.APIError as exc:
                if exc.code not in RETRYABLE_CODES or attempt == max_retries - 1:
                    raise
                time.sleep(min(60.0, 2**attempt) + random.uniform(0, 1))
                continue
            self.seconds_spent += time.perf_counter() - start
            self.api_calls += 1
            return normalise(np.array(result.embeddings[0].values))
        raise RuntimeError("unreachable")
