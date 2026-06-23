"""Read-only announcements feed (written by placement staff in the Django portal)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi_app.core.database import get_db
from fastapi_app.core.security import get_current_user
from fastapi_app.models.schemas import AnnouncementOut
from fastapi_app.models.sql_models import Announcement, User

router = APIRouter(prefix="/announcements", tags=["announcements"])


@router.get("", response_model=list[AnnouncementOut])
async def list_announcements(
    _: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    rows = (
        await db.execute(
            select(Announcement).order_by(Announcement.created_at.desc()).limit(50)
        )
    ).scalars().all()
    return rows
