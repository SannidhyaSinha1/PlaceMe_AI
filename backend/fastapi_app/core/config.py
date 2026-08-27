"""Application settings.

Every external service is optional: with no env vars at all the API boots on
a local SQLite file, and Gmail/LLM features degrade gracefully with clear
error messages instead of crashing. Set the corresponding keys (see
.env.example) to switch each feature on.
"""

from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]  # .../backend
REPO_ROOT = BACKEND_DIR.parent

# Make keys visible to libraries that read os.environ directly.
load_dotenv(REPO_ROOT / ".env", override=False)
load_dotenv(override=False)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(str(REPO_ROOT / ".env"), ".env"),
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "PlaceMe AI"

    # Deployment environment: "development" (default) or "production".
    # Production refuses to boot with insecure defaults (see main.py).
    environment: str = "development"

    # JWT
    secret_key: str = "dev-only-secret-change-me"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24

    # Key for encrypting sensitive columns (Gmail tokens) at rest.
    # Falls back to secret_key when unset; set a dedicated value in production.
    token_encryption_key: str = ""

    # Per-IP rate limiting on auth/sync endpoints (in-memory, no Redis).
    rate_limit_enabled: bool = True

    # Database — Supabase/Postgres URL, else a local SQLite file.
    supabase_db_url: str = ""

    # Google OAuth (Gmail inbox sync)
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/auth/gmail/callback"

    # LLMs used to extract company details out of an email
    groq_api_key: str = ""
    gemini_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"
    gemini_model: str = "gemini-3.6-flash"

    # Restrict Gmail sync to emails from this sender only
    placement_email_sender: str = "helpdesk.cdc@vit.ac.in"

    # How far back to look for placement emails (Gmail search unit)
    placement_email_since: str = "180d"

    frontend_origin: str = "http://localhost:3000"

    @property
    def is_production(self) -> bool:
        return self.environment.strip().lower() in ("production", "prod")

    @property
    def using_default_secret(self) -> bool:
        return self.secret_key == "dev-only-secret-change-me"

    @property
    def sqlalchemy_url(self) -> str:
        """Async SQLAlchemy URL: Supabase Postgres, or local SQLite fallback."""
        url = self.supabase_db_url
        if not url:
            return f"sqlite+aiosqlite:///{REPO_ROOT / 'placementor.db'}"
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return url

    @property
    def llm_configured(self) -> bool:
        return bool(self.groq_api_key or self.gemini_api_key)

    @property
    def gmail_oauth_configured(self) -> bool:
        return bool(self.google_client_id and self.google_client_secret)


@lru_cache
def get_settings() -> Settings:
    return Settings()
