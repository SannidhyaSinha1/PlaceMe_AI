"""Gmail sync: fetch placement emails and parse each one into an opportunity."""

from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi_app.core.database import get_db
from fastapi_app.core.ratelimit import RateLimit
from fastapi_app.core.security import get_current_user
from fastapi_app.models.sql_models import Opportunity, User
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

    # Skip emails already imported: re-extracting them would overwrite good
    # data with a heuristic guess whenever the LLM is down/rate-limited.
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

    created = 0
    for email in emails:
        msg_id = email.get("gmail_message_id")
        if not msg_id or msg_id in already_imported:
            continue

        # Extraction runs LLM chains / heuristics synchronously — off the loop.
        data = await asyncio.to_thread(
            pipeline.extract, email.get("subject", ""), email.get("body", "")
        )
        await pipeline.upsert_opportunity_from_extract(db, data, source_email_id=msg_id)
        created += 1

    await db.commit()
    return {"fetched": len(emails), "new_opportunities": created}
