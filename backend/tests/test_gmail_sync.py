"""Gmail sync: parses new emails once, skips already-imported on re-sync."""

import pytest
from sqlalchemy import select, update

from fastapi_app.core.database import SessionLocal
from fastapi_app.models.sql_models import Opportunity, User
from fastapi_app.services import gmail_service

FAKE_EMAILS = [
    {
        "gmail_message_id": "msg-001",
        "subject": "Internship at SyncTest Labs",
        "body": "SyncTest Labs hiring interns. Min CGPA 7. Skills: python.",
        "sender": "cdc@college.edu",
    },
    {
        "gmail_message_id": "msg-002",
        "subject": "TestCorp hackathon registration",
        "body": "Join the TestCorp hackathon. Deadline: 2026-09-01.",
        "sender": "cdc@college.edu",
    },
]


@pytest.fixture
async def gmail_student(client, student, monkeypatch):
    """Student with (fake) Gmail tokens and a stubbed Gmail fetch."""
    async with SessionLocal() as session:
        await session.execute(
            update(User)
            .where(User.id == student["user_id"])
            .values(gmail_access_token="fake-token", gmail_refresh_token="fake-refresh")
        )
        await session.commit()
    monkeypatch.setattr(
        gmail_service, "fetch_placement_emails", lambda *a, **k: list(FAKE_EMAILS)
    )
    return student


async def test_sync_imports_then_skips(client, gmail_student):
    r = await client.post("/gmail/sync", headers=gmail_student["headers"])
    assert r.status_code == 200, r.text
    assert r.json() == {"fetched": 2, "new_opportunities": 2}

    async with SessionLocal() as session:
        rows = (
            await session.execute(
                select(Opportunity).where(
                    Opportunity.source_email_id.in_(["msg-001", "msg-002"])
                )
            )
        ).scalars().all()
        assert len(rows) == 2
        original_names = {o.source_email_id: o.company_name for o in rows}
        by_id = {o.source_email_id: o for o in rows}
        # Company details really came out of the email body.
        assert by_id["msg-001"].opportunity_type == "Internship"
        assert "python" in (by_id["msg-001"].required_skills or [])
        assert by_id["msg-002"].deadline.isoformat() == "2026-09-01"

    # Re-sync: same emails come back — all must be skipped, data untouched.
    r = await client.post("/gmail/sync", headers=gmail_student["headers"])
    assert r.status_code == 200
    assert r.json() == {"fetched": 2, "new_opportunities": 0}

    async with SessionLocal() as session:
        rows = (
            await session.execute(
                select(Opportunity).where(
                    Opportunity.source_email_id.in_(["msg-001", "msg-002"])
                )
            )
        ).scalars().all()
        assert {o.source_email_id: o.company_name for o in rows} == original_names


async def test_sync_requires_gmail_connection(client):
    r = await client.post(
        "/auth/register", json={"email": "nogmail@test.co", "password": "test-password-123"}
    )
    headers = {"Authorization": f"Bearer {r.json()['access_token']}"}
    r = await client.post("/gmail/sync", headers=headers)
    assert r.status_code == 400
