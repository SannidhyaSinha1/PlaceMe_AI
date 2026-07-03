"""Student profile CRUD + resume upload/parse."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi_app.core.database import get_db
from fastapi_app.core.security import get_current_user
from fastapi_app.models.schemas import ProfileIn, ProfileOut
from fastapi_app.models.sql_models import StudentProfile, User

router = APIRouter(prefix="/profile", tags=["profile"])


async def _get_or_create_profile(db: AsyncSession, user_id: int) -> StudentProfile:
    profile = (
        await db.execute(select(StudentProfile).where(StudentProfile.user_id == user_id))
    ).scalar_one_or_none()
    if profile is None:
        profile = StudentProfile(user_id=user_id)
        db.add(profile)
        await db.flush()
    return profile


@router.get("/me", response_model=ProfileOut)
async def get_my_profile(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    profile = await _get_or_create_profile(db, user.id)
    await db.commit()
    return profile


@router.put("/me", response_model=ProfileOut)
async def update_my_profile(
    payload: ProfileIn, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    profile = await _get_or_create_profile(db, user.id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(profile, field, value)
    await db.commit()
    await db.refresh(profile)
    return profile


@router.post("/resume", response_model=ProfileOut)
async def upload_resume(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if file.content_type not in ("application/pdf", "application/octet-stream") and not (
        file.filename or ""
    ).lower().endswith(".pdf"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Resume must be a PDF")

    file_bytes = await file.read()
    if len(file_bytes) > 8 * 1024 * 1024:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "Resume exceeds 8 MB")
    # Validate by content, not just the (client-supplied) extension/MIME type.
    if not file_bytes.startswith(b"%PDF"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "File is not a valid PDF")

    from fastapi_app.services.cloudinary_service import (
        delete_local,
    )
    from fastapi_app.services.cloudinary_service import (
        upload_resume as store_resume,
    )
    from fastapi_app.services.resume_parser import parse_resume

    # PDF parsing is CPU-bound and the upload is blocking HTTP — off the loop.
    parsed = await asyncio.to_thread(parse_resume, file_bytes)
    url = await asyncio.to_thread(store_resume, file_bytes, user.id)

    profile = await _get_or_create_profile(db, user.id)
    # Remove the previous locally-stored resume so old files don't linger.
    if profile.resume_url and profile.resume_url != url:
        await asyncio.to_thread(delete_local, profile.resume_url)
    profile.resume_url = url
    profile.resume_parsed = parsed
    # Merge newly parsed skills into the profile skill list.
    merged = list(dict.fromkeys([*(profile.skills or []), *parsed.get("skills", [])]))
    if merged:
        profile.skills = merged
    await db.commit()
    await db.refresh(profile)
    return profile
