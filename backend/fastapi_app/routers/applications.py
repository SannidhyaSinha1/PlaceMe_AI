"""Application tracker: create (mark interested), list, update status."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi_app.core.database import get_db
from fastapi_app.core.security import get_current_user, require_complete_profile
from fastapi_app.models.schemas import (
    ApplicationCreate,
    ApplicationOut,
    StatusUpdate,
)
from fastapi_app.models.sql_models import (
    APPLICATION_STATUSES,
    Application,
    Opportunity,
    StudentProfile,
    User,
)
from fastapi_app.services import pipeline

router = APIRouter(prefix="/applications", tags=["applications"])


@router.get("", response_model=list[ApplicationOut])
async def list_applications(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    apps = (
        await db.execute(
            select(Application)
            .where(Application.user_id == user.id)
            .order_by(Application.updated_at.desc())
        )
    ).scalars().all()
    return apps


@router.post("", response_model=ApplicationOut, status_code=status.HTTP_201_CREATED)
async def create_application(
    payload: ApplicationCreate,
    user: User = Depends(require_complete_profile),
    db: AsyncSession = Depends(get_db),
):
    """Mark an opportunity as 'Interested' — runs eligibility + schedules reminders."""
    opp = await db.get(Opportunity, payload.opportunity_id)
    if opp is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Opportunity not found")

    profile = (
        await db.execute(select(StudentProfile).where(StudentProfile.user_id == user.id))
    ).scalar_one_or_none()

    app = await pipeline.ensure_application(
        db, user.id, opp, profile.as_dict() if profile else None
    )
    await db.commit()
    await db.refresh(app)
    return app


@router.put("/{app_id}/status", response_model=ApplicationOut)
async def update_status(
    app_id: int,
    payload: StatusUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if payload.status not in APPLICATION_STATUSES:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"status must be one of {APPLICATION_STATUSES}",
        )
    app = await db.get(Application, app_id)
    if app is None or app.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Application not found")
    app.status = payload.status
    if payload.notes is not None:
        app.notes = payload.notes
    await db.commit()
    await db.refresh(app)
    return app


@router.delete("/{app_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_application(
    app_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    app = await db.get(Application, app_id)
    if app is None or app.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Application not found")
    await db.delete(app)
    await db.commit()
