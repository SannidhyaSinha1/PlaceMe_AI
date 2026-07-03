"""Rate limiting as a FastAPI dependency (moving window, in-memory).

Built directly on the `limits` library — no Redis needed, and per the
graceful-degradation rule a missing package must not stop the API from
booting: the dependency degrades to a no-op with a warning.

Usage:
    @router.post("/login", dependencies=[Depends(RateLimit("10/minute", scope="login"))])
"""

# NOTE: no `from __future__ import annotations` here — FastAPI must see the
# real `Request` annotation on RateLimit.__call__ to inject the request.
import logging

from fastapi import HTTPException, Request, status

from fastapi_app.core.config import get_settings

logger = logging.getLogger(__name__)

try:
    from limits import parse
    from limits.storage import MemoryStorage
    from limits.strategies import MovingWindowRateLimiter

    _strategy = MovingWindowRateLimiter(MemoryStorage())
    available = True
except ImportError:  # pragma: no cover - degraded boot
    logger.warning("`limits` not installed — rate limiting disabled")
    _strategy = None
    available = False


class RateLimit:
    """Per-client-IP rate limit for a named scope (endpoints sharing a scope
    share one bucket)."""

    def __init__(self, limit: str, *, scope: str):
        self.scope = scope
        self.item = parse(limit) if available else None

    async def __call__(self, request: Request) -> None:
        if self.item is None or not get_settings().rate_limit_enabled:
            return
        client_ip = request.client.host if request.client else "unknown"
        if not _strategy.hit(self.item, self.scope, client_ip):
            raise HTTPException(
                status.HTTP_429_TOO_MANY_REQUESTS,
                "Rate limit exceeded — try again shortly",
            )
