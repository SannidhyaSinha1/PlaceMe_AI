"""Data layer: Supabase PostgreSQL (SQLAlchemy async) + MongoDB Atlas (motor).

Postgres holds the relational core (users, profiles, opportunities,
applications, reminders, announcements). Mongo holds bulky documents — raw
emails, AI content, company research reports — to keep the free 500 MB
Postgres tier lean.

With SUPABASE_DB_URL unset the app uses a local SQLite file; with MONGO_URI
unset every Mongo-backed feature simply no-ops (callers get None collections).
"""

import asyncio
import logging
from collections.abc import AsyncIterator

from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from fastapi_app.core.config import BACKEND_DIR, get_settings

logger = logging.getLogger(__name__)
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


def _run_migrations(stamp_baseline: bool) -> None:
    """Run Alembic programmatically (sync — call from a worker thread)."""
    from alembic import command
    from alembic.config import Config

    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "migrations"))
    if stamp_baseline:
        # Pre-Alembic database: its tables already match the baseline.
        command.stamp(cfg, "0001")
    command.upgrade(cfg, "head")


async def init_models() -> None:
    """Bring the schema up to date on boot.

    Preferred path: Alembic migrations (handles adding columns/indexes to
    existing databases). Databases created before Alembic are stamped at the
    baseline revision first. If Alembic isn't installed or fails, fall back to
    the old idempotent create_all so a zero-config boot always works.
    """

    # Ensure Base.metadata is populated even if no router imported the models.
    from fastapi_app.models import sql_models  # noqa: F401

    def _existing_state(conn) -> tuple[bool, bool]:
        insp = inspect(conn)
        return insp.has_table("users"), insp.has_table("alembic_version")

    async with engine.begin() as conn:
        has_tables, has_alembic = await conn.run_sync(_existing_state)

    try:
        # env.py calls asyncio.run(), so this must not run on the event loop.
        await asyncio.to_thread(_run_migrations, has_tables and not has_alembic)
        return
    except ModuleNotFoundError:
        logger.info("Alembic not installed — falling back to create_all")
    except Exception as exc:  # noqa: BLE001 - degrade, never block boot
        logger.warning("Alembic migration failed (%s) — falling back to create_all", exc)

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
