"""
LLM client abstraction and adapters.

Provides:
- ``LLMClient`` — abstract interface
- ``MockLLMClient`` — deterministic, no external calls (CI/demo default)
- ``OpenAIClient`` — real OpenAI API with streaming and retry

When ``LLM_PROVIDER=mock`` or no API key is configured the system uses
``MockLLMClient`` so the full application remains functional.
"""

from __future__ import annotations

import abc
import asyncio
import logging
import os
import re
import time
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


# ── Abstract base ────────────────────────────────────────────────────


class LLMClient(abc.ABC):
    """Abstract LLM client interface."""

    @abc.abstractmethod
    async def complete(self, messages: List[Dict[str, str]]) -> str:
        """Return a single completion string."""
        ...

    @abc.abstractmethod
    async def stream_chat(
        self,
        messages: List[Dict[str, str]],
        on_token: Callable[[str], Any],
        session_id: str = "",
        stop_tokens: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Stream tokens via *on_token* callback.

        Returns a metadata dict with at least
        ``prompt_tokens``, ``completion_tokens``.
        """
        ...

    @abc.abstractmethod
    def get_token_usage(self, response_meta: Dict[str, Any]) -> Dict[str, Any]:
        """Extract normalised usage info from response metadata."""
        ...


# ── Mock adapter ─────────────────────────────────────────────────────


_MOCK_RESPONSE = (
    "Based on the contract data in the current scope, "
    "I can see {count} contracts with a total spend of €{spend:.2f}. "
    "The largest contract is worth €{max_val:.2f}. "
    "This is a mock response — configure an LLM API key "
    "for real analysis."
)


class MockLLMClient(LLMClient):
    """Deterministic mock — always returns a template response.

    Designed for CI, demos, and when no API key is configured.
    """

    def __init__(self, context_summary: Optional[Dict[str, Any]] = None):
        self._ctx = context_summary or {
            "count": 0,
            "spend": 0.0,
            "max_val": 0.0,
        }

    async def complete(self, messages: List[Dict[str, str]]) -> str:
        text = _MOCK_RESPONSE.format(**self._ctx)
        return text

    async def stream_chat(
        self,
        messages: List[Dict[str, str]],
        on_token: Callable[[str], Any],
        session_id: str = "",
        stop_tokens: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        text = await self.complete(messages)
        prompt_tokens = sum(len(m.get("content", "")) for m in messages) // 4
        completion_tokens = len(text) // 4

        # Yield one token per word to mimic streaming
        words = text.split(" ")
        for i, word in enumerate(words):
            token = word if i == len(words) - 1 else word + " "
            await on_token(token)
            await asyncio.sleep(0)  # yield control

        return {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
        }

    def get_token_usage(self, response_meta: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "prompt_tokens": response_meta.get("prompt_tokens", 0),
            "completion_tokens": response_meta.get("completion_tokens", 0),
            "total_cost_usd": 0.0,
        }


# ── OpenAI adapter ───────────────────────────────────────────────────


class OpenAIClient(LLMClient):
    """OpenAI API adapter with streaming and retry.

    Only active when ``OPENAI_API_KEY`` is set **and** the ``openai``
    package is installed.  Otherwise falls back to ``MockLLMClient``.
    """

    _MAX_RETRIES = 3
    _BASE_DELAY = 1.0  # seconds

    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o-mini"):
        self._api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self._model = model
        self._client: Any = None
        self._circuit_failures = 0
        self._circuit_open = False

        if self._api_key:
            try:
                import openai  # type: ignore

                self._client = openai.AsyncOpenAI(api_key=self._api_key)
            except ImportError:
                logger.warning(
                    "openai package not installed — OpenAIClient disabled"
                )

    @property
    def available(self) -> bool:
        return self._client is not None and not self._circuit_open

    # ── retry wrapper ────────────────────────────────────────────────

    async def _with_retry(self, coro_factory):
        """Call *coro_factory()* with exponential-backoff retry."""
        last_exc: Optional[Exception] = None
        for attempt in range(self._MAX_RETRIES):
            try:
                result = await coro_factory()
                self._circuit_failures = 0
                return result
            except Exception as exc:
                last_exc = exc
                status = getattr(exc, "status_code", None) or getattr(
                    exc, "status", None
                )
                if status in (429, 503):
                    delay = self._BASE_DELAY * (2**attempt)
                    logger.warning(
                        "OpenAI %s — retry %d/%d in %.1fs",
                        status,
                        attempt + 1,
                        self._MAX_RETRIES,
                        delay,
                    )
                    await asyncio.sleep(delay)
                else:
                    break  # non-retryable
        # exhausted retries
        self._circuit_failures += 1
        if self._circuit_failures >= self._MAX_RETRIES:
            self._circuit_open = True
            logger.error("OpenAI circuit breaker opened after %d failures", self._circuit_failures)
        raise last_exc  # type: ignore[misc]

    # ── complete ─────────────────────────────────────────────────────

    async def complete(self, messages: List[Dict[str, str]]) -> str:
        if not self.available:
            raise RuntimeError("OpenAI client not available")

        async def _call():
            resp = await self._client.chat.completions.create(
                model=self._model,
                messages=messages,
            )
            return resp.choices[0].message.content

        return await self._with_retry(_call)

    # ── stream ───────────────────────────────────────────────────────

    async def stream_chat(
        self,
        messages: List[Dict[str, str]],
        on_token: Callable[[str], Any],
        session_id: str = "",
        stop_tokens: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        if not self.available:
            raise RuntimeError("OpenAI client not available")

        prompt_tokens = 0
        completion_tokens = 0

        async def _call():
            nonlocal prompt_tokens, completion_tokens
            stream = await self._client.chat.completions.create(
                model=self._model,
                messages=messages,
                stream=True,
                stream_options={"include_usage": True},
                stop=stop_tokens,
            )
            async for chunk in stream:
                if chunk.usage:
                    prompt_tokens = chunk.usage.prompt_tokens
                    completion_tokens = chunk.usage.completion_tokens
                if chunk.choices and chunk.choices[0].delta.content:
                    await on_token(chunk.choices[0].delta.content)
            return True

        await self._with_retry(_call)

        return {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
        }

    def get_token_usage(self, response_meta: Dict[str, Any]) -> Dict[str, Any]:
        prompt = response_meta.get("prompt_tokens", 0)
        completion = response_meta.get("completion_tokens", 0)
        # Approximate cost for gpt-4o-mini (as of 2025)
        cost = (prompt * 0.00015 + completion * 0.0006) / 1000
        return {
            "prompt_tokens": prompt,
            "completion_tokens": completion,
            "total_cost_usd": round(cost, 6),
        }


# ── Factory ──────────────────────────────────────────────────────────


def create_llm_client(
    provider: str = "mock",
    api_key: str = "",
    **kwargs,
) -> LLMClient:
    """Create an LLM client based on provider string.

    Falls back to ``MockLLMClient`` when the requested provider
    is not available or the key is absent.
    """
    if provider == "openai" and api_key:
        client = OpenAIClient(api_key=api_key, **kwargs)
        if client.available:
            logger.info("Using OpenAI LLM client (model=%s)", kwargs.get("model", "gpt-4o-mini"))
            return client
        logger.warning("OpenAI client not available — falling back to mock")
    elif provider not in ("mock", ""):
        if not api_key:
            logger.warning(
                "LLM_PROVIDER=%s but no API key configured — using mock",
                provider,
            )
        else:
            logger.warning(
                "LLM_PROVIDER=%s is not directly supported — using mock",
                provider,
            )
    return MockLLMClient(**kwargs) if "context_summary" in kwargs else MockLLMClient()
