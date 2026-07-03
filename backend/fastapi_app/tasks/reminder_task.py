"""Celery: send due deadline reminders via Gmail SMTP (Beat: every hour)."""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime

from sqlalchemy import select

from fastapi_app.core.database import SessionLocal
from fastapi_app.models.sql_models import Application, Opportunity, Reminder, User
from fastapi_app.services import email_service
from fastapi_app.tasks.celery_app import celery

logger = logging.getLogger(__name__)


@celery.task(name="fastapi_app.tasks.reminder_task.dispatch_reminders")
def dispatch_reminders() -> dict:
    return asyncio.run(_dispatch_reminders())


async def _dispatch_reminders() -> dict:
    now = datetime.now(UTC)
    sent = 0
    async with SessionLocal() as db:
        due = (
            await db.execute(
                select(Reminder).where(
                    Reminder.sent.is_(False), Reminder.remind_at <= now
                )
            )
        ).scalars().all()

        for reminder in due:
            app = await db.get(Application, reminder.application_id)
            if app is None:
                reminder.sent = True
                continue
            user = await db.get(User, app.user_id)
            opp = await db.get(Opportunity, app.opportunity_id)
            if not user or not opp or not opp.deadline:
                reminder.sent = True
                continue

            days_left = (opp.deadline - now.date()).days
            ok = email_service.send_deadline_reminder(
                user.email,
                opp.company_name or "A company",
                opp.role or opp.opportunity_type,
                max(days_left, 0),
                opp.deadline.isoformat(),
            )
            reminder.sent = True
            sent += int(ok)

        await db.commit()
    return {"reminders_processed": len(due), "emails_sent": sent}
