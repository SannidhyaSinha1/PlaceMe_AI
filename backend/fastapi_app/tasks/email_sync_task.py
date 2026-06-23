"""Celery: periodic Gmail sync for every connected user (Beat: every 30 min)."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from fastapi_app.core.database import SessionLocal, mongo_collection
from fastapi_app.models.sql_models import Opportunity, StudentProfile, User
from fastapi_app.services import gmail_service, pipeline
from fastapi_app.tasks.celery_app import celery

logger = logging.getLogger(__name__)


@celery.task(name="fastapi_app.tasks.email_sync_task.sync_all_users")
def sync_all_users() -> dict:
    return asyncio.run(_sync_all_users())


@celery.task(name="fastapi_app.tasks.email_sync_task.sync_user")
def sync_user(user_id: int) -> dict:
    return asyncio.run(_sync_user(user_id))


async def _sync_all_users() -> dict:
    async with SessionLocal() as db:
        users = (
            await db.execute(select(User).where(User.gmail_refresh_token.is_not(None)))
        ).scalars().all()
    total = 0
    for user in users:
        try:
            result = await _sync_user(user.id)
            total += result.get("new_opportunities", 0)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Sync failed for user %s: %s", user.id, exc)
    return {"users_synced": len(users), "new_opportunities": total}


async def _sync_user(user_id: int) -> dict:
    from fastapi_app.tasks.ai_pipeline_task import run_ai_pipeline

    async with SessionLocal() as db:
        user = await db.get(User, user_id)
        if user is None or not (user.gmail_refresh_token or user.gmail_access_token):
            return {"new_opportunities": 0}

        emails = await asyncio.to_thread(
            gmail_service.fetch_placement_emails,
            user.gmail_access_token,
            user.gmail_refresh_token,
        )
        profile = (
            await db.execute(
                select(StudentProfile).where(StudentProfile.user_id == user_id)
            )
        ).scalar_one_or_none()
        profile_dict = profile.as_dict() if profile else None

        raw_col = mongo_collection("raw_emails")
        new_opp_ids: list[int] = []
        for email in emails:
            msg_id = email.get("gmail_message_id")
            if not msg_id:
                continue
            exists = (
                await db.execute(
                    select(Opportunity.id).where(Opportunity.source_email_id == msg_id)
                )
            ).scalar_one_or_none()
            if exists:
                continue
            if raw_col is not None:
                await _store_raw(raw_col, user_id, email)

            data = pipeline.extract_and_classify(
                email.get("subject", ""), email.get("body", "")
            )
            opp = await pipeline.upsert_opportunity_from_extract(
                db, data, source_email_id=msg_id
            )
            await pipeline.ensure_application(db, user_id, opp, profile_dict)
            new_opp_ids.append(opp.id)

        await db.commit()

    # Kick off heavy AI enrichment per new opportunity (async subtasks).
    for opp_id in new_opp_ids:
        run_ai_pipeline.delay(user_id, opp_id)

    return {"new_opportunities": len(new_opp_ids)}


async def _store_raw(col, user_id: int, email: dict):
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
                    "stored_at": datetime.now(timezone.utc).isoformat(),
                }
            },
            upsert=True,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("raw_email store failed: %s", exc)


@celery.task(name="fastapi_app.tasks.email_sync_task.purge_old_raw_emails")
def purge_old_raw_emails(days: int = 30) -> dict:
    return asyncio.run(_purge_old_raw_emails(days))


async def _purge_old_raw_emails(days: int) -> dict:
    col = mongo_collection("raw_emails")
    if col is None:
        return {"deleted": 0}
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    res = await col.delete_many({"stored_at": {"$lt": cutoff}})
    return {"deleted": res.deleted_count}
