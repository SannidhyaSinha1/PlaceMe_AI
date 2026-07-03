"""Manual Gmail sync endpoint (the same logic Celery Beat runs every 30 min)."""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi_app.core.database import get_db, mongo_collection
from fastapi_app.core.ratelimit import RateLimit
from fastapi_app.core.security import get_current_user
from fastapi_app.models.sql_models import Opportunity, StudentProfile, User
from fastapi_app.services import gmail_service, pipeline

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/gmail", tags=["gmail"])


@router.post("/sync", dependencies=[Depends(RateLimit("3/minute", scope="gmail-sync"))])
async def sync_my_inbox(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    if not user.gmail_refresh_token and not user.gmail_access_token:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Connect Gmail first")

    # Gmail API is blocking → run in a worker thread.
    try:
        emails = await asyncio.to_thread(
            gmail_service.fetch_placement_emails,
            user.gmail_access_token,
            user.gmail_refresh_token,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("Gmail fetch failed for user %s: %s", user.id, exc)
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Gmail fetch failed") from exc

    profile = (
        await db.execute(select(StudentProfile).where(StudentProfile.user_id == user.id))
    ).scalar_one_or_none()
    profile_dict = profile.as_dict() if profile else None

    raw_col = mongo_collection("raw_emails")
    created = 0

    # Skip emails already imported: re-extracting them would overwrite good
    # data with a heuristic guess whenever the LLM is down/rate-limited.
    # Use the re-extraction backfill script for intentional re-processing.
    msg_ids = [m for m in (e.get("gmail_message_id") for e in emails) if m]
    already_imported = set(
        (
            await db.execute(
                select(Opportunity.source_email_id).where(
                    Opportunity.source_email_id.in_(msg_ids)
                )
            )
        ).scalars()
    ) if msg_ids else set()

    for email in emails:
        msg_id = email.get("gmail_message_id")
        if not msg_id or msg_id in already_imported:
            continue

        if raw_col is not None:
            await _store_raw_email(raw_col, user.id, email)

        # Extraction runs LLM chains / heuristics synchronously — off the loop.
        data = await asyncio.to_thread(
            pipeline.extract_and_classify, email.get("subject", ""), email.get("body", "")
        )
        opp = await pipeline.upsert_opportunity_from_extract(db, data, source_email_id=msg_id)
        await pipeline.ensure_application(db, user.id, opp, profile_dict)
        created += 1

    await db.commit()
    return {"fetched": len(emails), "new_opportunities": created}


async def _store_raw_email(col, user_id: int, email: dict):
    try:
        await col.update_one(
            {"gmail_message_id": email["gmail_message_id"], "user_id": user_id},
            {
                "$set": {
                    "user_id": user_id,
                    "subject": email.get("subject"),
                    "body": email.get("body"),
                    "sender": email.get("sender"),
                    "received_at": email.get("received_at"),
                    "processed": True,
                    "stored_at": datetime.now(UTC).isoformat(),
                }
            },
            upsert=True,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("Storing raw email failed: %s", exc)
