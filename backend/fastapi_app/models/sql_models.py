"""SQLAlchemy models: the account that owns a mailbox, and what we parsed from it.

JSON columns are JSONB on Postgres and plain JSON on the SQLite dev fallback.
"""

from datetime import date, datetime

from sqlalchemy import (
    JSON,
    Date,
    DateTime,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from fastapi_app.core.crypto import EncryptedStr
from fastapi_app.core.database import Base

JsonCol = JSON().with_variant(JSONB(), "postgresql")

OPPORTUNITY_TYPES = [
    "Internship",
    "Full-Time Placement",
    "Hackathon",
    "Competition",
    "Workshop",
    "Scholarship",
    "Other",
]


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    # OAuth tokens are encrypted at rest (Fernet) via the EncryptedStr type.
    gmail_access_token: Mapped[str | None] = mapped_column(EncryptedStr)
    gmail_refresh_token: Mapped[str | None] = mapped_column(EncryptedStr)
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Opportunity(Base):
    """One placement email, parsed into structured company details."""

    __tablename__ = "opportunities"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_name: Mapped[str | None] = mapped_column(String(255), index=True)
    role: Mapped[str | None] = mapped_column(String(255))
    opportunity_type: Mapped[str] = mapped_column(String(50), default="Other", index=True)
    description: Mapped[str | None] = mapped_column(Text)
    deadline: Mapped[date | None] = mapped_column(Date, index=True)
    salary_stipend: Mapped[str | None] = mapped_column(String(100))
    job_location: Mapped[str | None] = mapped_column(String(255))
    required_skills: Mapped[list | None] = mapped_column(JsonCol)
    # Whatever eligibility bar the email stated (min CGPA, branches, …), kept
    # as free-form JSON purely for display.
    eligibility_criteria: Mapped[dict | None] = mapped_column(JsonCol)
    source_email_id: Mapped[str | None] = mapped_column(String(255), unique=True)
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
