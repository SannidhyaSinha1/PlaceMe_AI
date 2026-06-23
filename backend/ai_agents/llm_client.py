"""LLM access: Groq (primary) with Google Gemini (fallback).

Heavy LangChain imports are deferred so the API can boot without the AI
extras installed. `llm_available()` lets callers degrade gracefully, and
`invoke_with_fallback()` implements implementation-rule #5: on a Groq 429 /
rate-limit / transient error, retry with exponential backoff, then fall back
to Gemini.
"""

from __future__ import annotations

import logging
import time
from functools import lru_cache
from typing import Optional

from fastapi_app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class LLMUnavailable(RuntimeError):
    """Raised when no LLM provider is configured or all providers failed."""


@lru_cache(maxsize=1)
def _groq():
    if not settings.groq_api_key:
        return None
    try:
        from langchain_groq import ChatGroq

        return ChatGroq(
            model=settings.groq_model,
            temperature=0,
            api_key=settings.groq_api_key,
            max_retries=0,  # we manage retries/fallback ourselves
        )
    except Exception as exc:  # pragma: no cover - import/config failure
        logger.warning("Groq init failed: %s", exc)
        return None


@lru_cache(maxsize=1)
def _gemini():
    if not settings.gemini_api_key:
        return None
    try:
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(
            model=settings.gemini_model,
            temperature=0,
            google_api_key=settings.gemini_api_key,
        )
    except Exception as exc:  # pragma: no cover
        logger.warning("Gemini init failed: %s", exc)
        return None


def get_llm():
    """Primary LLM (Groq) or the Gemini fallback or None."""
    return _groq() or _gemini()


def llm_available() -> bool:
    return get_llm() is not None


def _is_rate_limit(exc: Exception) -> bool:
    name = exc.__class__.__name__.lower()
    text = str(exc).lower()
    return (
        "ratelimit" in name
        or "429" in text
        or "rate limit" in text
        or "quota" in text
        or "resourceexhausted" in name
    )


def invoke_with_fallback(chain, payload: dict, *, max_retries: int = 3):
    """Run a LangChain runnable on Groq with backoff, falling back to Gemini.

    `chain` is built lazily from a provider via `build(llm)` so we can swap the
    underlying model on fallback. Either pass a callable `build` through
    `payload['_build']`, or a pre-bound chain (no provider swap then).
    """
    build = payload.pop("_build", None)
    providers = [p for p in (_groq(), _gemini()) if p is not None]
    if not providers:
        raise LLMUnavailable("No LLM configured (set GROQ_API_KEY or GEMINI_API_KEY)")

    last_exc: Optional[Exception] = None
    for provider in providers:
        runnable = build(provider) if build else chain
        for attempt in range(max_retries):
            try:
                return runnable.invoke(payload)
            except Exception as exc:  # noqa: BLE001 - provider-agnostic
                last_exc = exc
                if _is_rate_limit(exc) and attempt < max_retries - 1:
                    backoff = 2**attempt
                    logger.warning("LLM rate-limited, retrying in %ss", backoff)
                    time.sleep(backoff)
                    continue
                logger.warning(
                    "LLM provider %s failed: %s", provider.__class__.__name__, exc
                )
                break  # move to next provider
    raise LLMUnavailable(f"All LLM providers failed: {last_exc}")
