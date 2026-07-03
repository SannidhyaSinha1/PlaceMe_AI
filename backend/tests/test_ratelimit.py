"""RateLimit dependency: unit-tested directly so endpoint tests stay unthrottled."""

import pytest
from fastapi import HTTPException

from fastapi_app.core.config import get_settings
from fastapi_app.core.ratelimit import RateLimit, available


@pytest.fixture(autouse=True)
def enable_ratelimit(monkeypatch):
    # conftest disables limiting globally (shared client IP); re-enable here.
    monkeypatch.setattr(get_settings(), "rate_limit_enabled", True)


class _FakeClient:
    def __init__(self, host):
        self.host = host


class _FakeRequest:
    def __init__(self, host):
        self.client = _FakeClient(host)


@pytest.mark.skipif(not available, reason="limits not installed")
async def test_limit_hits_then_blocks():
    rl = RateLimit("3/minute", scope="unit-test-scope")
    req = _FakeRequest("10.1.2.3")
    for _ in range(3):
        await rl(req)  # allowed
    with pytest.raises(HTTPException) as exc:
        await rl(req)
    assert exc.value.status_code == 429


@pytest.mark.skipif(not available, reason="limits not installed")
async def test_limit_is_per_ip():
    rl = RateLimit("2/minute", scope="unit-test-scope-2")
    await rl(_FakeRequest("10.0.0.1"))
    await rl(_FakeRequest("10.0.0.1"))
    # A different client is unaffected.
    await rl(_FakeRequest("10.0.0.2"))
