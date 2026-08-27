"""Test fixtures: hermetic app on a temp SQLite DB with all integrations off.

The environment MUST be pinned before any fastapi_app import — settings are
lru_cached and the engine is created at import time.
"""

import os
import tempfile

_TEST_DB = os.path.join(tempfile.mkdtemp(prefix="placeme-tests-"), "test.db")
os.environ["SUPABASE_DB_URL"] = f"sqlite+aiosqlite:///{_TEST_DB}"
# Force every external integration off so tests exercise the fallbacks
# deterministically (empty string beats the .env values: load_dotenv uses
# override=False and pydantic prefers real env vars over the env file).
for _key in (
    "GROQ_API_KEY", "GEMINI_API_KEY", "GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET",
):
    os.environ[_key] = ""
os.environ["ENVIRONMENT"] = "development"
# All tests share one client IP; the limiter is unit-tested directly instead.
os.environ["RATE_LIMIT_ENABLED"] = "false"

import httpx  # noqa: E402
import pytest  # noqa: E402

from fastapi_app.main import app, lifespan  # noqa: E402


@pytest.fixture(scope="session")
async def client():
    """App client over ASGI (no network), with the lifespan (migrations) run."""
    async with lifespan(app):
        transport = httpx.ASGITransport(app=app, client=("127.0.0.1", 9999))
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
            yield c


_user_seq = 0


@pytest.fixture
async def student(client):
    """A registered user; returns auth headers plus their id/email."""
    global _user_seq
    _user_seq += 1
    email = f"student{_user_seq}@test.co"
    r = await client.post(
        "/auth/register", json={"email": email, "password": "test-password-123"}
    )
    assert r.status_code == 201, r.text
    body = r.json()
    return {
        "headers": {"Authorization": f"Bearer {body['access_token']}"},
        "email": email,
        "user_id": body["user"]["id"],
    }
