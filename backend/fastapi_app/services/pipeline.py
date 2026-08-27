"""Email → Opportunity row.

The whole job of this app: take one placement email, pull the company details
out of it, and persist them (deduplicated by Gmail message id).
"""

from __future__ import annotations

import logging
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ai_agents import email_extractor
from fastapi_app.models.sql_models import Opportunity

logger = logging.getLogger(__name__)


def extract(subject: str, body: str) -> dict:
    """Run the email extractor and return its fields as a plain dict."""
    data = email_extractor.extract_from_email(subject, body).model_dump()
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
    db: AsyncSession, data: dict, source_email_id: str | None = None
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
        opp = Opportunity(source_email_id=source_email_id)
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
