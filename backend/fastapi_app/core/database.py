"""Data layer: Supabase PostgreSQL (SQLAlchemy async) + MongoDB Atlas (motor).

Postgres holds the relational core (users, profiles, opportunities,
applications, reminders, announcements). Mongo holds bulky documents — raw
emails, AI content, company research reports — to keep the free 500 MB
Postgres tier lean.

With SUPABASE_DB_URL unset the app uses a local SQLite file; with MONGO_URI
unset every Mongo-backed feature simply no-ops (callers get None collections).
"""

from typing import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from fastapi_app.core.config import get_settings

settings = get_settings()

# SQLite is single-writer: give concurrent writers a grace period to wait for
# the lock instead of failing immediately with "database is locked".
_url = settings.sqlalchemy_url
_connect_args = {"timeout": 30} if _url.startswith("sqlite") else {}
engine = create_async_engine(_url, pool_pre_ping=True, connect_args=_connect_args)
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session


async def init_models() -> None:
    """Create missing tables on boot (idempotent; db/schema.sql mirrors this)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


# ── MongoDB Atlas (motor — async, per implementation rule #1) ─────────────
_mongo_client = None


def mongo_db():
    """The motor database, or None when MONGO_URI is not configured."""
    global _mongo_client
    if not settings.mongo_uri:
        return None
    if _mongo_client is None:
        from motor.motor_asyncio import AsyncIOMotorClient

        _mongo_client = AsyncIOMotorClient(settings.mongo_uri)
    return _mongo_client["placementor"]


def mongo_collection(name: str):
    """A motor collection (raw_emails / company_reports / ai_content), or None."""
    db = mongo_db()
    return db[name] if db is not None else None
