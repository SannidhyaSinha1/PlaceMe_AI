"""Auth + Gmail OAuth routes.

The account exists for one reason: to hold this person's Gmail tokens so the
sync knows which mailbox to read.
"""

from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi_app.core.config import get_settings
from fastapi_app.core.database import get_db
from fastapi_app.core.ratelimit import RateLimit
from fastapi_app.core.security import (
    create_access_token,
    decode_token,
    get_current_user,
    hash_password,
    verify_password,
)
from fastapi_app.models.schemas import LoginIn, RegisterIn, TokenOut, UserOut
from fastapi_app.models.sql_models import User

logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter(prefix="/auth", tags=["auth"])


def _user_out(user: User) -> UserOut:
    return UserOut(
        id=user.id,
        email=user.email,
        gmail_connected=bool(user.gmail_refresh_token),
        created_at=user.created_at,
    )


@router.post(
    "/register",
    response_model=TokenOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(RateLimit("5/minute", scope="auth-register"))],
)
async def register(payload: RegisterIn, db: AsyncSession = Depends(get_db)):
    existing = (
        await db.execute(select(User).where(User.email == payload.email.lower()))
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")

    # bcrypt is ~100ms of CPU — keep it off the event loop.
    password_hash = await asyncio.to_thread(hash_password, payload.password)
    user = User(email=payload.email.lower(), password_hash=password_hash)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return TokenOut(access_token=create_access_token(user.id), user=_user_out(user))


@router.post(
    "/login",
    response_model=TokenOut,
    dependencies=[Depends(RateLimit("10/minute", scope="auth-login"))],
)
async def login(payload: LoginIn, db: AsyncSession = Depends(get_db)):
    user = (
        await db.execute(select(User).where(User.email == payload.email.lower()))
    ).scalar_one_or_none()
    if not user or not await asyncio.to_thread(
        verify_password, payload.password, user.password_hash
    ):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")
    return TokenOut(access_token=create_access_token(user.id), user=_user_out(user))


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(get_current_user)):
    return _user_out(user)


# ── Gmail OAuth ────────────────────────────────────────────────────────────
@router.get("/gmail/connect")
async def gmail_connect(user: User = Depends(get_current_user)):
    """Return the Google consent URL. State carries a short-lived JWT for the user."""
    if not settings.gmail_oauth_configured:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Gmail OAuth not configured")
    from fastapi_app.services import gmail_service

    state = create_access_token(user.id, expires_minutes=15, purpose="gmail_oauth")
    return {"auth_url": gmail_service.build_auth_url(state)}


@router.get("/gmail/callback")
async def gmail_callback(
    code: str | None = None, state: str | None = None, db: AsyncSession = Depends(get_db)
):
    """Google redirects here after consent; persist tokens and bounce to frontend."""
    if not code or not state:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Missing code/state")
    from fastapi_app.services import gmail_service

    payload = decode_token(state)
    if payload.get("purpose") != "gmail_oauth":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid OAuth state")
    user = await db.get(User, int(payload["sub"]))
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")

    try:
        tokens = gmail_service.exchange_code(code, state=state)
    except Exception as exc:  # noqa: BLE001
        logger.warning("OAuth code exchange failed: %s", exc)
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "OAuth exchange failed") from exc

    user.gmail_access_token = tokens.get("access_token")
    if tokens.get("refresh_token"):
        user.gmail_refresh_token = tokens["refresh_token"]
    await db.commit()
    return RedirectResponse(f"{settings.frontend_origin}/?gmail=connected")
