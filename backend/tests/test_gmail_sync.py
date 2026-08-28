"""Gmail sync: parses new emails once, batches the backlog, skips re-imports."""

import pytest
from sqlalchemy import select, update

from fastapi_app.core.database import SessionLocal
from fastapi_app.models.sql_models import Opportunity, User
from fastapi_app.services import gmail_service

FAKE_EMAILS = {
    "msg-001": {
        "gmail_message_id": "msg-001",
        "subject": "Internship at SyncTest Labs",
        "body": "SyncTest Labs hiring interns. Min CGPA 7. Skills: python.",
        "sender": "cdc@college.edu",
    },
    "msg-002": {
        "gmail_message_id": "msg-002",
        "subject": "TestCorp hackathon registration",
        "body": "Join the TestCorp hackathon. Deadline: 2026-09-01.",
        "sender": "cdc@college.edu",
    },
}


@pytest.fixture
async def gmail_student(client, student, monkeypatch):
    """Student with (fake) Gmail tokens and a stubbed Gmail API."""
    async with SessionLocal() as session:
        await session.execute(
            update(User)
            .where(User.id == student["user_id"])
            .values(gmail_access_token="fake-token", gmail_refresh_token="fake-refresh")
        )
        await session.commit()
    monkeypatch.setattr(
        gmail_service, "list_placement_message_ids", lambda *a, **k: list(FAKE_EMAILS)
    )
    monkeypatch.setattr(
        gmail_service, "fetch_email_by_id", lambda a, r, mid: FAKE_EMAILS[mid]
    )
    return student


async def test_sync_imports_then_skips(client, gmail_student):
    r = await client.post("/gmail/sync", headers=gmail_student["headers"])
    assert r.status_code == 200, r.text
    assert r.json() == {"found": 2, "new_opportunities": 2, "remaining": 0}

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
    assert r.json() == {"found": 2, "new_opportunities": 0, "remaining": 0}

    async with SessionLocal() as session:
        rows = (
            await session.execute(
                select(Opportunity).where(
                    Opportunity.source_email_id.in_(["msg-001", "msg-002"])
                )
            )
        ).scalars().all()
        assert {o.source_email_id: o.company_name for o in rows} == original_names


BACKLOG_EMAILS = {
    f"backlog-{i}": {
        "gmail_message_id": f"backlog-{i}",
        "subject": f"Internship at Backlog Corp {i}",
        "body": f"Backlog Corp {i} is hiring interns. Skills: python.",
        "sender": "cdc@college.edu",
    }
    for i in range(2)
}


async def test_sync_batches_the_backlog(client, gmail_student, monkeypatch):
    """A capped sync parses part of the backlog and reports what is left."""
    # Distinct ids: the client/DB are session-scoped, so the emails from the
    # test above are already imported and would leave nothing pending.
    monkeypatch.setattr(
        gmail_service, "list_placement_message_ids", lambda *a, **k: list(BACKLOG_EMAILS)
    )
    monkeypatch.setattr(
        gmail_service, "fetch_email_by_id", lambda a, r, mid: BACKLOG_EMAILS[mid]
    )
    r = await client.post("/gmail/sync?limit=1", headers=gmail_student["headers"])
    assert r.status_code == 200, r.text
    assert r.json() == {"found": 2, "new_opportunities": 1, "remaining": 1}

    # The next run picks up the one that was left, not the one already done.
    r = await client.post("/gmail/sync?limit=1", headers=gmail_student["headers"])
    assert r.json() == {"found": 2, "new_opportunities": 1, "remaining": 0}


async def test_sync_requires_gmail_connection(client):
    r = await client.post(
        "/auth/register", json={"email": "nogmail@test.co", "password": "test-password-123"}
    )
    headers = {"Authorization": f"Bearer {r.json()['access_token']}"}
    r = await client.post("/gmail/sync", headers=headers)
    assert r.status_code == 400
