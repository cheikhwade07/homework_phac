"""LLM client: schema-constrained JSON generation with retries and a disk cache.

The rest of the package depends only on the ``LLMClient`` protocol, so the
provider can be swapped (for example for a locally hosted model) without
touching the classifier or the evaluation code.
"""

from __future__ import annotations

import hashlib
import json
import os
import random
import sqlite3
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

DEFAULT_MODEL = "gemini-2.5-flash"
DEFAULT_CACHE = Path(".cache/llm.sqlite")
RETRYABLE_CODES = {429, 500, 502, 503, 504}


@dataclass(frozen=True)
class LLMResponse:
    text: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    latency_s: float = 0.0
    cached: bool = False


class LLMClient(Protocol):
    model: str

    def generate_json(self, system: str, user: str, schema: dict[str, Any]) -> LLMResponse:
        """Return a response whose text is JSON matching ``schema``."""
        ...


class ResponseCache:
    """SQLite cache keyed by a hash of everything that determines a response."""

    def __init__(self, path: Path = DEFAULT_CACHE):
        path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS responses (key TEXT PRIMARY KEY, value TEXT NOT NULL)"
        )
        self._lock = threading.Lock()

    @staticmethod
    def key(**parts: Any) -> str:
        blob = json.dumps(parts, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()

    def get(self, key: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT value FROM responses WHERE key = ?", (key,)
            ).fetchone()
        return json.loads(row[0]) if row else None

    def put(self, key: str, value: dict[str, Any]) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT OR REPLACE INTO responses (key, value) VALUES (?, ?)",
                (key, json.dumps(value, ensure_ascii=False)),
            )
            self._conn.commit()


class GeminiClient:
    """Gemini via the google-genai SDK, deterministic settings, cached and retried."""

    def __init__(
        self,
        model: str | None = None,
        cache: ResponseCache | None = None,
        max_retries: int = 6,
        thinking_budget: int | None = None,
    ):
        from dotenv import load_dotenv
        from google import genai

        load_dotenv()
        self.model = model or os.getenv("CASEFILTER_MODEL", DEFAULT_MODEL)
        if thinking_budget is None:
            thinking_budget = int(os.getenv("CASEFILTER_THINKING_BUDGET", "0"))
        self.thinking_budget = thinking_budget
        self.cache = cache if cache is not None else ResponseCache()
        self.max_retries = max_retries
        self._client = genai.Client()

    def generate_json(self, system: str, user: str, schema: dict[str, Any]) -> LLMResponse:
        key = ResponseCache.key(
            model=self.model,
            system=system,
            user=user,
            schema=schema,
            temperature=0,
            thinking_budget=self.thinking_budget,
        )
        hit = self.cache.get(key)
        if hit is not None:
            return LLMResponse(**{**hit, "latency_s": 0.0, "cached": True})

        response = self._call_with_retries(system, user, schema)
        self.cache.put(key, {k: v for k, v in response.__dict__.items() if k != "cached"})
        return response

    def _call_with_retries(self, system: str, user: str, schema: dict[str, Any]) -> LLMResponse:
        from google.genai import errors, types

        config = types.GenerateContentConfig(
            system_instruction=system or None,
            temperature=0,
            response_mime_type="application/json",
            response_schema=schema,
            thinking_config=types.ThinkingConfig(thinking_budget=self.thinking_budget),
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        )
        for attempt in range(self.max_retries):
            start = time.perf_counter()
            try:
                result = self._client.models.generate_content(
                    model=self.model, contents=user, config=config
                )
            except errors.APIError as exc:
                if exc.code not in RETRYABLE_CODES or attempt == self.max_retries - 1:
                    raise
                time.sleep(min(60.0, 2**attempt) + random.uniform(0, 1))
                continue
            usage = result.usage_metadata
            return LLMResponse(
                text=result.text or "",
                model=self.model,
                input_tokens=(usage.prompt_token_count or 0) if usage else 0,
                output_tokens=(usage.candidates_token_count or 0) if usage else 0,
                latency_s=time.perf_counter() - start,
            )
        raise RuntimeError("unreachable")
