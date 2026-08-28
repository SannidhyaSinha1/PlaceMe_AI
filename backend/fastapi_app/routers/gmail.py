"""Gmail sync: fetch placement emails and parse each one into an opportunity."""

from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi_app.core.database import get_db
from fastapi_app.core.ratelimit import RateLimit
from fastapi_app.core.security import get_current_user
from fastapi_app.models.sql_models import Opportunity, User
from fastapi_app.services import gmail_service, pipeline

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/gmail", tags=["gmail"])

# Emails parsed per sync. Each one costs a Gmail message fetch plus an LLM
# call, so an unbounded first sync would run for minutes and be cut off by a
# free-tier request timeout. Syncing repeatedly walks through the backlog.
SYNC_BATCH_SIZE = 15


@router.post("/sync", dependencies=[Depends(RateLimit("3/minute", scope="gmail-sync"))])
async def sync_my_inbox(
    limit: int = Query(SYNC_BATCH_SIZE, ge=1, le=50, description="Emails to parse this run"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not user.gmail_refresh_token and not user.gmail_access_token:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Connect Gmail first")

    # Gmail API is blocking → run in a worker thread.
    try:
        msg_ids = await asyncio.to_thread(
            gmail_service.list_placement_message_ids,
            user.gmail_access_token,
            user.gmail_refresh_token,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("Gmail listing failed for user %s: %s", user.id, exc)
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Gmail fetch failed") from exc

    # Skip emails already imported: re-extracting them would overwrite good
    # data with a heuristic guess whenever the LLM is down/rate-limited.
    already_imported = set(
        (
            await db.execute(
                select(Opportunity.source_email_id).where(
                    Opportunity.source_email_id.in_(msg_ids)
                )
            )
        ).scalars()
    ) if msg_ids else set()

    pending = [m for m in msg_ids if m not in already_imported]
    batch = pending[:limit]

    created = 0
    for msg_id in batch:
        try:
            email = await asyncio.to_thread(
                gmail_service.fetch_email_by_id,
                user.gmail_access_token,
                user.gmail_refresh_token,
                msg_id,
            )
        except Exception as exc:  # noqa: BLE001 - one bad message must not sink the batch
            logger.warning("Skipping message %s: %s", msg_id, exc)
            continue

        # Extraction runs LLM chains / heuristics synchronously — off the loop.
        data = await asyncio.to_thread(
            pipeline.extract, email.get("subject", ""), email.get("body", "")
        )
        await pipeline.upsert_opportunity_from_extract(db, data, source_email_id=msg_id)
        created += 1

    await db.commit()
    return {
        "found": len(msg_ids),
        "new_opportunities": created,
        "remaining": max(len(pending) - created, 0),
    }
