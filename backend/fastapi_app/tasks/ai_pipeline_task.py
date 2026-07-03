"""Celery: heavy AI enrichment per new opportunity.

Fan-out subtasks (research, resume optimize, cover letter) each retry with
exponential backoff on rate limits (rule #5; the LLM client also falls back to
Gemini internally). Triggered by the email sync task after an opportunity row
exists.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime

from sqlalchemy import select

from ai_agents import company_researcher, cover_letter_gen, resume_optimizer
from fastapi_app.core.database import SessionLocal, mongo_collection
from fastapi_app.models.sql_models import Application, Opportunity, StudentProfile
from fastapi_app.services import email_service
from fastapi_app.tasks.celery_app import celery

logger = logging.getLogger(__name__)

_RETRY = {"max_retries": 4, "default_retry_delay": 8, "retry_backoff": True}


@celery.task(name="fastapi_app.tasks.ai_pipeline_task.run_ai_pipeline")
def run_ai_pipeline(user_id: int, opportunity_id: int) -> dict:
    """Orchestrate the per-opportunity AI fan-out + notify the student."""
    research_company.delay(opportunity_id)
    optimize_resume.delay(user_id, opportunity_id)
    generate_cover_letter.delay(user_id, opportunity_id)
    notify_student.delay(user_id, opportunity_id)
    return {"dispatched": 4, "opportunity_id": opportunity_id}


@celery.task(bind=True, name="fastapi_app.tasks.ai_pipeline_task.research_company", **_RETRY)
def research_company(self, opportunity_id: int):
    try:
        return asyncio.run(_research(opportunity_id))
    except Exception as exc:  # noqa: BLE001
        raise self.retry(exc=exc) from exc


async def _research(opportunity_id: int):
    async with SessionLocal() as db:
        opp = await db.get(Opportunity, opportunity_id)
        if opp is None or not opp.company_name:
            return {"skipped": True}
    return await company_researcher.research_company(opp.company_name, opportunity_id)


@celery.task(bind=True, name="fastapi_app.tasks.ai_pipeline_task.optimize_resume", **_RETRY)
def optimize_resume(self, user_id: int, opportunity_id: int):
    try:
        return asyncio.run(_optimize_resume(user_id, opportunity_id))
    except Exception as exc:  # noqa: BLE001
        raise self.retry(exc=exc) from exc


async def _optimize_resume(user_id: int, opportunity_id: int):
    async with SessionLocal() as db:
        opp = await db.get(Opportunity, opportunity_id)
        profile = (
            await db.execute(
                select(StudentProfile).where(StudentProfile.user_id == user_id)
            )
        ).scalar_one_or_none()
        if opp is None or profile is None or not profile.resume_parsed:
            return {"skipped": True}
        jd = " ".join(
            p for p in [opp.role, opp.description, " ".join(opp.required_skills or [])] if p
        )
        analysis = resume_optimizer.analyze_resume(
            profile.resume_parsed, jd, opp.required_skills or []
        )
    await _store_ai(user_id, opportunity_id, "resume_analysis", analysis)
    return {"ats_score": analysis["ats_score"]}


@celery.task(bind=True, name="fastapi_app.tasks.ai_pipeline_task.generate_cover_letter", **_RETRY)
def generate_cover_letter(self, user_id: int, opportunity_id: int):
    try:
        return asyncio.run(_generate_cover_letter(user_id, opportunity_id))
    except Exception as exc:  # noqa: BLE001
        raise self.retry(exc=exc) from exc


async def _generate_cover_letter(user_id: int, opportunity_id: int):
    async with SessionLocal() as db:
        opp = await db.get(Opportunity, opportunity_id)
        profile = (
            await db.execute(
                select(StudentProfile).where(StudentProfile.user_id == user_id)
            )
        ).scalar_one_or_none()
        if opp is None or profile is None or not profile.resume_parsed:
            return {"skipped": True}

        summary = ""
        reports = mongo_collection("company_reports")
        if reports is not None and opp.company_name:
            cached = await reports.find_one({"company_name": opp.company_name})
            if cached:
                summary = cached.get("overview", "")

        result = await cover_letter_gen.generate_and_store(
            user_id, {**opp.as_dict(), "id": opp.id}, profile.resume_parsed, summary
        )

        app = (
            await db.execute(
                select(Application).where(
                    Application.user_id == user_id,
                    Application.opportunity_id == opportunity_id,
                )
            )
        ).scalar_one_or_none()
        if app and result.get("pdf_url"):
            app.cover_letter_url = result["pdf_url"]
            await db.commit()

    await _store_ai(user_id, opportunity_id, "cover_letter", result)
    return {"pdf_url": result.get("pdf_url")}


@celery.task(name="fastapi_app.tasks.ai_pipeline_task.notify_student")
def notify_student(user_id: int, opportunity_id: int):
    return asyncio.run(_notify_student(user_id, opportunity_id))


async def _notify_student(user_id: int, opportunity_id: int):
    from fastapi_app.models.sql_models import User

    async with SessionLocal() as db:
        user = await db.get(User, user_id)
        opp = await db.get(Opportunity, opportunity_id)
        app = (
            await db.execute(
                select(Application).where(
                    Application.user_id == user_id,
                    Application.opportunity_id == opportunity_id,
                )
            )
        ).scalar_one_or_none()
    if not user or not opp:
        return {"sent": False}
    sent = email_service.send_new_opportunity(
        user.email,
        opp.company_name or "A company",
        opp.role or opp.opportunity_type,
        app.eligibility_status if app else "Unknown",
    )
    return {"sent": sent}


async def _store_ai(user_id: int, opp_id: int, content_type: str, data: dict):
    col = mongo_collection("ai_content")
    if col is None:
        return
    try:
        await col.update_one(
            {"user_id": user_id, "opportunity_id": opp_id, "type": content_type},
            {
                "$set": {
                    "user_id": user_id,
                    "opportunity_id": opp_id,
                    "type": content_type,
                    "content": data,
                    "ats_score": data.get("ats_score"),
                    "skill_gaps": data.get("skill_gaps"),
                    "generated_at": datetime.now(UTC).isoformat(),
                }
            },
            upsert=True,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("ai_content store failed: %s", exc)
