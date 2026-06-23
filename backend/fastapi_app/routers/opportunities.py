"""Opportunity listing with filters/sort + per-student eligibility enrichment."""

from __future__ import annotations

import asyncio
from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi_app.core.database import get_db
from fastapi_app.core.security import get_current_admin, get_current_user
from fastapi_app.models.schemas import (
    EligibilityOut,
    OpportunityIn,
    OpportunityOut,
)
from fastapi_app.models.sql_models import Application, Opportunity, StudentProfile, User
from fastapi_app.services import pipeline, gmail_service

router = APIRouter(prefix="/opportunities", tags=["opportunities"])

_SORTS = {
    "deadline": Opportunity.deadline.asc(),
    "salary": Opportunity.salary_stipend.desc(),
    "company": Opportunity.company_name.asc(),
    "newest": Opportunity.created_at.desc(),
}


async def _profile_dict(db: AsyncSession, user_id: int) -> Optional[dict]:
    profile = (
        await db.execute(select(StudentProfile).where(StudentProfile.user_id == user_id))
    ).scalar_one_or_none()
    return profile.as_dict() if profile else None


def _serialize(opp: Opportunity, verdict: dict, app: Optional[Application]) -> OpportunityOut:
    out = OpportunityOut.model_validate(opp)
    out.eligibility = EligibilityOut(**verdict)
    if opp.source_email_id:
        out.email_link = gmail_service.message_web_link(opp.source_email_id)
    if app:
        out.application_id = app.id
        out.application_status = app.status
    return out


@router.get("", response_model=list[OpportunityOut])
async def list_opportunities(
    type: Optional[str] = Query(None, description="Filter by opportunity_type"),
    eligible_only: bool = False,
    applied: Optional[bool] = None,
    upcoming: bool = Query(False, description="Deadline within 14 days"),
    search: Optional[str] = None,
    sort: str = Query("newest", enum=list(_SORTS.keys())),
    limit: int = Query(50, le=200),
    offset: int = 0,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Opportunity)
    if type:
        stmt = stmt.where(Opportunity.opportunity_type == type)
    if upcoming:
        stmt = stmt.where(
            Opportunity.deadline.is_not(None),
            Opportunity.deadline >= date.today(),
            Opportunity.deadline <= date.today() + timedelta(days=14),
        )
    if search:
        like = f"%{search}%"
        stmt = stmt.where(
            Opportunity.company_name.ilike(like) | Opportunity.role.ilike(like)
        )
    stmt = stmt.order_by(_SORTS[sort]).limit(limit).offset(offset)

    opps = (await db.execute(stmt)).scalars().all()

    # Pull this user's applications once for enrichment.
    apps = {
        a.opportunity_id: a
        for a in (
            await db.execute(select(Application).where(Application.user_id == user.id))
        ).scalars()
    }
    profile = await _profile_dict(db, user.id)

    results: list[OpportunityOut] = []
    for opp in opps:
        verdict = pipeline.evaluate_for_student(opp, profile)
        app = apps.get(opp.id)
        if eligible_only and verdict.get("status") not in ("Eligible", "Potentially Eligible"):
            continue
        if applied is True and app is None:
            continue
        if applied is False and app is not None:
            continue
        results.append(_serialize(opp, verdict, app))
    return results


@router.get("/{opp_id}", response_model=OpportunityOut)
async def get_opportunity(
    opp_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    opp = await db.get(Opportunity, opp_id)
    if opp is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Opportunity not found")
    profile = await _profile_dict(db, user.id)
    verdict = pipeline.evaluate_for_student(opp, profile)
    app = (
        await db.execute(
            select(Application).where(
                Application.user_id == user.id, Application.opportunity_id == opp.id
            )
        )
    ).scalar_one_or_none()
    return _serialize(opp, verdict, app)


@router.get("/{opp_id}/email")
async def get_opportunity_email(
    opp_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """Fetch the original Gmail email for this opportunity."""
    opp = await db.get(Opportunity, opp_id)
    if opp is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Opportunity not found")
    if not opp.source_email_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No source email for this opportunity")
    if not user.gmail_access_token:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Connect Gmail first")
    try:
        email = await asyncio.to_thread(
            gmail_service.fetch_email_by_id,
            user.gmail_access_token,
            user.gmail_refresh_token,
            opp.source_email_id,
        )
    except Exception as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"Gmail fetch failed: {exc}")
    return email


@router.post("", response_model=OpportunityOut, status_code=status.HTTP_201_CREATED)
async def create_opportunity(
    payload: OpportunityIn,
    _: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Manual creation (admin) — bypasses the Gmail pipeline."""
    opp = Opportunity(**payload.model_dump(), source="manual")
    db.add(opp)
    await db.commit()
    await db.refresh(opp)
    return _serialize(opp, {"status": "Unknown", "reasons": [], "score": None}, None)
