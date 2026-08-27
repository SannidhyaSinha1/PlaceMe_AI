"""Read-only listing of the company details parsed out of placement emails."""

from __future__ import annotations

import asyncio
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi_app.core.database import get_db
from fastapi_app.core.security import get_current_user
from fastapi_app.models.schemas import EmailOut, OpportunityOut
from fastapi_app.models.sql_models import Opportunity, User
from fastapi_app.services import gmail_service

router = APIRouter(prefix="/opportunities", tags=["opportunities"])

_SORTS = {
    "newest": Opportunity.created_at.desc(),
    "deadline": Opportunity.deadline.asc(),
    "company": Opportunity.company_name.asc(),
}


def _serialize(opp: Opportunity) -> OpportunityOut:
    out = OpportunityOut.model_validate(opp)
    if opp.source_email_id:
        out.email_link = gmail_service.message_web_link(opp.source_email_id)
    return out


@router.get("", response_model=list[OpportunityOut])
async def list_opportunities(
    type: str | None = Query(None, max_length=50, description="Filter by opportunity_type"),
    upcoming: bool = Query(False, description="Deadline within 14 days"),
    search: str | None = Query(None, max_length=200),
    sort: str = Query("newest", enum=list(_SORTS.keys())),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    _: User = Depends(get_current_user),
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
    return [_serialize(o) for o in opps]


@router.get("/{opp_id}", response_model=OpportunityOut)
async def get_opportunity(
    opp_id: int, _: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    opp = await db.get(Opportunity, opp_id)
    if opp is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Opportunity not found")
    return _serialize(opp)


@router.get("/{opp_id}/email", response_model=EmailOut)
async def get_opportunity_email(
    opp_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """Fetch the original Gmail email this opportunity was parsed from."""
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
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Gmail fetch failed") from exc
    return email
