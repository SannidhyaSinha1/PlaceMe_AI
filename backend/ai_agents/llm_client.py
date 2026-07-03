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


# Cumulative counters since boot — surfaced on /health so degraded providers
# are visible instead of silent. Plain dict mutation is atomic enough for
# counters (GIL); exactness under heavy threading isn't required here.
_stats: dict = {"calls": 0, "successes": 0, "failures": 0, "fallback_successes": 0,
                "by_provider": {}, "last_error": None}


def get_stats() -> dict:
    return {**_stats, "by_provider": dict(_stats["by_provider"])}


def _record(provider: str, ok: bool, latency_ms: float) -> None:
    p = _stats["by_provider"].setdefault(
        provider, {"successes": 0, "failures": 0, "total_latency_ms": 0.0}
    )
    p["successes" if ok else "failures"] += 1
    p["total_latency_ms"] += latency_ms


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

    _stats["calls"] += 1
    last_exc: Exception | None = None
    for p_idx, provider in enumerate(providers):
        pname = provider.__class__.__name__
        runnable = build(provider) if build else chain
        for attempt in range(max_retries):
            start = time.perf_counter()
            try:
                result = runnable.invoke(payload)
                latency_ms = (time.perf_counter() - start) * 1000
                _record(pname, True, latency_ms)
                _stats["successes"] += 1
                if p_idx > 0:
                    _stats["fallback_successes"] += 1
                logger.info(
                    "llm ok provider=%s attempt=%d fallback=%s latency_ms=%.0f",
                    pname, attempt + 1, p_idx > 0, latency_ms,
                )
                return result
            except Exception as exc:  # noqa: BLE001 - provider-agnostic
                latency_ms = (time.perf_counter() - start) * 1000
                _record(pname, False, latency_ms)
                last_exc = exc
                _stats["last_error"] = f"{pname}: {exc}"[:300]
                rate_limited = _is_rate_limit(exc)
                logger.warning(
                    "llm error provider=%s attempt=%d rate_limited=%s latency_ms=%.0f err=%s",
                    pname, attempt + 1, rate_limited, latency_ms, exc,
                )
                if rate_limited and attempt < max_retries - 1:
                    backoff = 2**attempt
                    logger.warning("LLM rate-limited, retrying in %ss", backoff)
                    time.sleep(backoff)
                    continue
                break  # move to next provider
    _stats["failures"] += 1
    raise LLMUnavailable(f"All LLM providers failed: {last_exc}")
