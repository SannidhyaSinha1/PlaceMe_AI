"""PlaceMentor AI — FastAPI student API entrypoint.

Boots on local SQLite with zero env vars; every external integration
(Supabase, MongoDB, Groq/Gemini, Gmail, Cloudinary, Tavily) activates when its
keys are present and degrades gracefully otherwise.
"""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from fastapi_app.core.config import get_settings
from fastapi_app.core.database import init_models
from fastapi_app.routers import (
    ai,
    analytics,
    announcements,
    applications,
    auth,
    gmail,
    opportunities,
    profile,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("placementor")
settings = get_settings()


def _enforce_production_safety() -> None:
    """Refuse to boot in production with insecure defaults."""
    if not settings.is_production:
        if settings.using_default_secret:
            logger.warning(
                "Using the built-in dev SECRET_KEY — set SECRET_KEY before deploying."
            )
        return
    problems = []
    if settings.using_default_secret:
        problems.append("SECRET_KEY is still the built-in dev value")
    if len(settings.secret_key) < 32:
        problems.append("SECRET_KEY must be at least 32 characters")
    if problems:
        raise RuntimeError(
            "Refusing to start in production: " + "; ".join(problems)
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    _enforce_production_safety()
    await init_models()
    os.makedirs(settings.faiss_index_dir, exist_ok=True)
    os.makedirs(settings.uploads_dir, exist_ok=True)

    from ai_agents import llm_client

    llm_ready = llm_client.llm_available()
    if settings.llm_configured and not llm_ready:
        logger.warning(
            "LLM keys are set but no provider client could be built — the AI "
            "pipeline will fall back to heuristics. Check the langchain-* package "
            "versions (langchain-core must match langchain-groq/google-genai)."
        )
    logger.info(
        "PlaceMentor AI up | db=%s | llm=%s | gmail_oauth=%s | cloudinary=%s | smtp=%s",
        "supabase" if settings.supabase_db_url else "sqlite",
        "active" if llm_ready else ("configured-but-broken" if settings.llm_configured else "off"),
        settings.gmail_oauth_configured,
        settings.cloudinary_configured,
        settings.smtp_configured,
    )
    yield


app = FastAPI(title=settings.app_name, version="1.0.0", lifespan=lifespan)


@app.middleware("http")
async def security_headers(request, call_next):
    """Add conservative security headers to every response."""
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    if settings.is_production:
        response.headers.setdefault(
            "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
        )
    return response


# In production only the configured frontend origin is allowed; localhost dev
# ports are permitted outside production for convenience.
_allowed_origins = [settings.frontend_origin]
if not settings.is_production:
    _allowed_origins += [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:5173",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=sorted(set(_allowed_origins)),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for r in (auth, profile, opportunities, applications, ai, analytics, gmail, announcements):
    app.include_router(r.router)

# Serve locally-stored PDFs when Cloudinary isn't configured.
os.makedirs(settings.uploads_dir, exist_ok=True)
app.mount("/files", StaticFiles(directory=settings.uploads_dir), name="files")


@app.get("/", tags=["health"])
async def root():
    return {"service": settings.app_name, "status": "ok", "docs": "/docs"}


@app.get("/health", tags=["health"])
async def health():
    from ai_agents import llm_client

    return {
        "status": "healthy",
        "database": "supabase" if settings.supabase_db_url else "sqlite",
        "mongo": bool(settings.mongo_uri),
        # `llm` reflects a real, importable provider client — not just key
        # presence. `llm_configured` shows whether keys are set at all.
        "llm": llm_client.llm_available(),
        "llm_configured": settings.llm_configured,
        "features": {
            "gmail_oauth": settings.gmail_oauth_configured,
            "cloudinary": settings.cloudinary_configured,
            "tavily": bool(settings.tavily_api_key),
            "smtp": settings.smtp_configured,
        },
    }
