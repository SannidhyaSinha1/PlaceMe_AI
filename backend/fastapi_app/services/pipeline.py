"""Shared AI pipeline orchestration (used by routers and Celery tasks).

Implements the per-email workflow: extract → classify → upsert opportunity →
eligibility → schedule reminders, plus helpers to enrich opportunities with a
student's eligibility for API responses. Heavy AI sub-steps (research, resume,
cover letter) are triggered by the Celery layer; here we keep the synchronous
core that must run for every opportunity.
"""

from __future__ import annotations

import logging
from datetime import UTC, date, datetime, time, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ai_agents import classifier, email_extractor
from fastapi_app.models.sql_models import (
    REMINDER_OFFSETS_DAYS,
    Application,
    Opportunity,
    Reminder,
)
from fastapi_app.services import eligibility_engine

logger = logging.getLogger(__name__)


def extract_and_classify(subject: str, body: str) -> dict:
    """Run the email extractor + zero-shot classifier; return a merged dict."""
    extracted = email_extractor.extract_from_email(subject, body)
    cls = classifier.classify(subject, body)
    data = extracted.model_dump()
    if cls.get("label"):
        data["opportunity_type"] = cls["label"]
    data["classification"] = cls
    # Use the email subject as company_name fallback so we never show "Unknown".
    if not data.get("company_name") and subject:
        data["company_name"] = subject.strip()
    return data


def _criteria_from_extract(data: dict) -> dict:
    return {
        "min_cgpa": data.get("min_cgpa"),
        "min_tenth": data.get("min_tenth"),
        "min_twelfth": data.get("min_twelfth"),
        "allowed_branches": data.get("allowed_branches"),
        "allowed_years": data.get("allowed_years"),
        "required_skills": data.get("required_skills") or [],
        "no_backlogs_required": data.get("no_backlogs_required"),
    }


def _parse_deadline(value) -> date | None:
    if not value:
        return None
    if isinstance(value, date):
        return value
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(str(value), fmt).date()
        except ValueError:
            continue
    return None


async def upsert_opportunity_from_extract(
    db: AsyncSession, data: dict, source_email_id: str | None = None, source: str = "email"
) -> Opportunity:
    """Create/update an Opportunity row from extracted fields (dedup by email id)."""
    opp = None
    if source_email_id:
        opp = (
            await db.execute(
                select(Opportunity).where(Opportunity.source_email_id == source_email_id)
            )
        ).scalar_one_or_none()

    if opp is None:
        opp = Opportunity(source_email_id=source_email_id, source=source)
        db.add(opp)

    opp.company_name = data.get("company_name") or opp.company_name or "Unknown"
    opp.role = data.get("role") or opp.role
    opp.opportunity_type = data.get("opportunity_type") or "Other"
    opp.description = data.get("summary") or opp.description
    opp.deadline = _parse_deadline(data.get("deadline")) or opp.deadline
    opp.salary_stipend = data.get("salary_stipend") or opp.salary_stipend
    opp.job_location = data.get("job_location") or opp.job_location
    opp.required_skills = data.get("required_skills") or []
    opp.eligibility_criteria = _criteria_from_extract(data)
    await db.flush()
    return opp


def evaluate_for_student(opp: Opportunity, profile: dict | None) -> dict:
    """Eligibility result for one opportunity + student profile."""
    return evaluate_batch_for_student([opp], profile)[0]


def evaluate_batch_for_student(
    opps: list[Opportunity], profile: dict | None
) -> list[dict]:
    """Eligibility results for many opportunities in one model call."""
    if not profile:
        return [
            {"status": "Unknown", "reasons": ["Complete your profile to check eligibility"], "score": None}
            for _ in opps
        ]
    return eligibility_engine.check_eligibility_batch(
        profile, [opp.eligibility_criteria or {} for opp in opps]
    )


async def ensure_application(
    db: AsyncSession, user_id: int, opp: Opportunity, profile: dict | None,
    status: str = "Interested",
) -> Application:
    """Create (or fetch) an application and stamp its eligibility verdict."""
    app = (
        await db.execute(
            select(Application).where(
                Application.user_id == user_id, Application.opportunity_id == opp.id
            )
        )
    ).scalar_one_or_none()

    verdict = evaluate_for_student(opp, profile)
    if app is None:
        app = Application(user_id=user_id, opportunity_id=opp.id, status=status)
        db.add(app)
    app.eligibility_status = verdict["status"]
    app.eligibility_reasons = verdict["reasons"]
    app.eligibility_score = verdict.get("score")
    await db.flush()
    await schedule_reminders(db, app, opp)
    return app


async def schedule_reminders(db: AsyncSession, app: Application, opp: Opportunity) -> None:
    """Insert 7d/3d/1d/0d reminder rows for an application's deadline (idempotent)."""
    if not opp.deadline:
        return
    existing = {
        r.reminder_type
        for r in (
            await db.execute(select(Reminder).where(Reminder.application_id == app.id))
        ).scalars()
    }
    today = date.today()
    for rtype, offset in REMINDER_OFFSETS_DAYS.items():
        if rtype in existing:
            continue
        remind_day = opp.deadline - timedelta(days=offset)
        if remind_day < today:
            continue
        remind_at = datetime.combine(remind_day, time(9, 0), tzinfo=UTC)
        db.add(
            Reminder(
                application_id=app.id, remind_at=remind_at,
                reminder_type=rtype, sent=False,
            )
        )
    await db.flush()
