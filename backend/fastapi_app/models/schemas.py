"""Pydantic v2 request/response schemas."""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ── Auth ──────────────────────────────────────────────────────────────────
class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class UserOut(ORMModel):
    id: int
    email: str
    gmail_connected: bool = False
    created_at: datetime | None = None


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ── Opportunities ─────────────────────────────────────────────────────────
class OpportunityOut(ORMModel):
    id: int
    company_name: str | None = None
    role: str | None = None
    opportunity_type: str = "Other"
    description: str | None = None
    deadline: date | None = None
    salary_stipend: str | None = None
    job_location: str | None = None
    required_skills: list[str] | None = None
    eligibility_criteria: dict | None = None
    source_email_id: str | None = None
    created_at: datetime | None = None
    # Direct Gmail link to the source email (not a DB column).
    email_link: str | None = None


class EmailOut(BaseModel):
    """The original Gmail message behind an opportunity."""

    gmail_message_id: str | None = None
    subject: str = ""
    sender: str = ""
    received_at: str = ""
    body: str = ""
