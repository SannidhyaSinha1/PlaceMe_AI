"""PlaceMe AI — FastAPI entrypoint.

One job: read placement emails from Gmail, parse the company details out of
them, and serve those to the frontend. Boots on local SQLite with zero env
vars; Gmail and the LLM activate when their keys are present and degrade
gracefully otherwise.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from fastapi_app.core.config import get_settings
from fastapi_app.core.database import init_models
from fastapi_app.routers import auth, gmail, opportunities

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
        raise RuntimeError("Refusing to start in production: " + "; ".join(problems))


@asynccontextmanager
async def lifespan(app: FastAPI):
    _enforce_production_safety()
    await init_models()

    from ai_agents import llm_client

    llm_ready = llm_client.llm_available()
    if settings.llm_configured and not llm_ready:
        logger.warning(
            "LLM keys are set but no provider client could be built — email "
            "parsing will fall back to heuristics. Check the langchain-* package "
            "versions (langchain-core must match langchain-groq/google-genai)."
        )
    logger.info(
        "PlaceMe AI up | db=%s | llm=%s | gmail_oauth=%s",
        "supabase" if settings.supabase_db_url else "sqlite",
        "active" if llm_ready else ("configured-but-broken" if settings.llm_configured else "off"),
        settings.gmail_oauth_configured,
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

for r in (auth, opportunities, gmail):
    app.include_router(r.router)


@app.get("/", tags=["health"])
async def root():
    return {"service": settings.app_name, "status": "ok", "docs": "/docs"}


@app.get("/health", tags=["health"])
async def health():
    from ai_agents import llm_client

    return {
        "status": "healthy",
        "database": "supabase" if settings.supabase_db_url else "sqlite",
        # `llm` reflects a real, importable provider client — not just key
        # presence. `llm_configured` shows whether keys are set at all.
        "llm": llm_client.llm_available(),
        "llm_configured": settings.llm_configured,
        # Cumulative call/failure/fallback counters since boot, per provider —
        # makes silent degradation to heuristics visible.
        "llm_stats": llm_client.get_stats(),
        "gmail_oauth": settings.gmail_oauth_configured,
    }
