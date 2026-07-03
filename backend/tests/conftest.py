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
    "GROQ_API_KEY", "GEMINI_API_KEY", "MONGO_URI", "TAVILY_API_KEY",
    "CLOUDINARY_CLOUD_NAME", "CLOUDINARY_API_KEY", "CLOUDINARY_API_SECRET",
    "GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "GMAIL_ADDRESS",
    "GMAIL_APP_PASSWORD",
):
    os.environ[_key] = ""
os.environ["ENVIRONMENT"] = "development"
os.environ["ADMIN_EMAILS"] = "admin@test.co"
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


@pytest.fixture
async def db_session():
    from fastapi_app.core.database import SessionLocal

    async with SessionLocal() as session:
        yield session


_user_seq = 0


@pytest.fixture
async def student(client):
    """A registered student with a complete profile; returns auth headers."""
    global _user_seq
    _user_seq += 1
    email = f"student{_user_seq}@test.co"
    r = await client.post(
        "/auth/register", json={"email": email, "password": "test-password-123"}
    )
    assert r.status_code == 201, r.text
    headers = {"Authorization": f"Bearer {r.json()['access_token']}"}
    r = await client.put(
        "/profile/me",
        headers=headers,
        json={
            "name": "Test Student", "branch": "CSE", "current_year": 3,
            "cgpa": 8.5, "tenth_pct": 90, "twelfth_pct": 88,
            "active_backlogs": 0, "skills": ["python", "sql"],
        },
    )
    assert r.status_code == 200, r.text
    # The onboarding gate also requires an uploaded CV; set it directly.
    from sqlalchemy import select, update

    from fastapi_app.core.database import SessionLocal
    from fastapi_app.models.sql_models import StudentProfile, User

    async with SessionLocal() as session:
        uid = (
            await session.execute(select(User.id).where(User.email == email))
        ).scalar_one()
        await session.execute(
            update(StudentProfile)
            .where(StudentProfile.user_id == uid)
            .values(resume_url="/files/test.pdf", resume_parsed={"skills": ["python"]})
        )
        await session.commit()
    return {"headers": headers, "email": email, "user_id": uid}


@pytest.fixture
async def admin(client):
    email = "admin@test.co"
    r = await client.post(
        "/auth/register", json={"email": email, "password": "test-password-123"}
    )
    if r.status_code == 409:  # session-scoped client, admin may already exist
        r = await client.post(
            "/auth/login", json={"email": email, "password": "test-password-123"}
        )
    body = r.json()
    assert body["user"]["is_admin"] is True
    return {"headers": {"Authorization": f"Bearer {body['access_token']}"}}
