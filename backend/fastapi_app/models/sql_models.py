"""SQLAlchemy models for the relational core (Supabase PostgreSQL).

JSON columns are JSONB on Postgres and plain JSON on the SQLite dev fallback.
The Django admin portal maps onto these same tables with managed=False.
"""

from datetime import date, datetime
from typing import Optional

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

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

APPLICATION_STATUSES = [
    "Interested",
    "Applied",
    "Assessment Scheduled",
    "Interview Scheduled",
    "Offer Received",
    "Rejected",
]

REMINDER_OFFSETS_DAYS = {"7d": 7, "3d": 3, "1d": 1, "0d": 0}


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    # OAuth tokens are encrypted at rest (Fernet) via the EncryptedStr type.
    gmail_access_token: Mapped[str | None] = mapped_column(EncryptedStr)
    gmail_refresh_token: Mapped[str | None] = mapped_column(EncryptedStr)
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Loaded explicitly where needed (auth responses) — an implicit selectin
    # here costs an extra query on every authenticated request.
    profile: Mapped[Optional["StudentProfile"]] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    applications: Mapped[list["Application"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class StudentProfile(Base):
    __tablename__ = "student_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True
    )
    name: Mapped[str | None] = mapped_column(String(255))
    college: Mapped[str | None] = mapped_column(String(255))
    branch: Mapped[str | None] = mapped_column(String(100))
    current_year: Mapped[int | None] = mapped_column(SmallInteger)
    cgpa: Mapped[float | None] = mapped_column(Numeric(4, 2))
    tenth_pct: Mapped[float | None] = mapped_column(Numeric(5, 2))
    twelfth_pct: Mapped[float | None] = mapped_column(Numeric(5, 2))
    active_backlogs: Mapped[int | None] = mapped_column(SmallInteger, default=0)
    skills: Mapped[list | None] = mapped_column(JsonCol)
    resume_url: Mapped[str | None] = mapped_column(Text)
    resume_parsed: Mapped[dict | None] = mapped_column(JsonCol)
    # Raw LaTeX (.tex) source of the résumé — lets the AI edit it in place
    # (bold/add/remove keywords) and return tailored, compilable LaTeX.
    resume_latex: Mapped[str | None] = mapped_column(Text)

    user: Mapped["User"] = relationship(back_populates="profile")

    @property
    def profile_complete(self) -> bool:
        """True once every eligibility field is filled and a CV is uploaded.

        This is the gate for unlocking the student-facing app (admins exempt).
        """
        if not self.resume_url:
            return False
        required = (
            self.name, self.branch, self.current_year,
            self.cgpa, self.tenth_pct, self.twelfth_pct,
        )
        return all(v is not None and v != "" for v in required)

    def as_dict(self) -> dict:
        """Plain dict consumed by the eligibility engine and AI agents."""

        def _f(value):
            return float(value) if value is not None else None

        return {
            "name": self.name,
            "college": self.college,
            "branch": self.branch,
            "current_year": self.current_year,
            "cgpa": _f(self.cgpa),
            "tenth_pct": _f(self.tenth_pct),
            "twelfth_pct": _f(self.twelfth_pct),
            "active_backlogs": self.active_backlogs or 0,
            "skills": self.skills or [],
            "resume_parsed": self.resume_parsed or {},
        }


class Opportunity(Base):
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
    eligibility_criteria: Mapped[dict | None] = mapped_column(JsonCol)
    source_email_id: Mapped[str | None] = mapped_column(String(255), unique=True)
    source: Mapped[str] = mapped_column(String(20), default="manual")
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    applications: Mapped[list["Application"]] = relationship(back_populates="opportunity")

    def as_dict(self) -> dict:
        """Plain dict consumed by the AI agents (resume optimizer, cover letter)."""
        return {
            "company_name": self.company_name,
            "role": self.role,
            "opportunity_type": self.opportunity_type,
            "description": self.description,
            "deadline": self.deadline.isoformat() if self.deadline else None,
            "salary_stipend": self.salary_stipend,
            "job_location": self.job_location,
            "required_skills": self.required_skills or [],
            "eligibility_criteria": self.eligibility_criteria or {},
        }


class Application(Base):
    __tablename__ = "applications"
    __table_args__ = (
        UniqueConstraint("user_id", "opportunity_id", name="uq_user_opportunity"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    opportunity_id: Mapped[int] = mapped_column(
        ForeignKey("opportunities.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[str] = mapped_column(String(50), default="Interested")
    eligibility_status: Mapped[str | None] = mapped_column(String(30))
    eligibility_reasons: Mapped[list | None] = mapped_column(JsonCol)
    eligibility_score: Mapped[float | None] = mapped_column(Float)
    cover_letter_url: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # No API path reads application.user — don't eager-load it (it cascaded a
    # users + student_profiles query onto every applications fetch).
    user: Mapped["User"] = relationship(back_populates="applications")
    # ApplicationOut serializes the nested opportunity, so keep the batched
    # selectin (one IN query per result set).
    opportunity: Mapped["Opportunity"] = relationship(
        back_populates="applications", lazy="selectin"
    )
    reminders: Mapped[list["Reminder"]] = relationship(
        back_populates="application", cascade="all, delete-orphan"
    )


class Reminder(Base):
    __tablename__ = "reminders"

    id: Mapped[int] = mapped_column(primary_key=True)
    application_id: Mapped[int] = mapped_column(
        ForeignKey("applications.id", ondelete="CASCADE"), index=True
    )
    remind_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    reminder_type: Mapped[str] = mapped_column(String(20))  # 7d / 3d / 1d / 0d
    sent: Mapped[bool] = mapped_column(Boolean, default=False)

    # The reminder task loads applications explicitly; eager-loading here
    # chained application → opportunity queries onto every reminder fetch.
    application: Mapped["Application"] = relationship(back_populates="reminders")


class Announcement(Base):
    """Broadcasts written by placement staff in the Django portal, read here."""

    __tablename__ = "announcements"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255))
    body: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
