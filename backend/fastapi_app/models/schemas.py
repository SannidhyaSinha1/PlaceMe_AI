"""Pydantic v2 request/response schemas."""

from datetime import date, datetime
from typing import Optional

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
    is_admin: bool = False
    gmail_connected: bool = False
    profile_complete: bool = False
    created_at: Optional[datetime] = None


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ── Profile ───────────────────────────────────────────────────────────────
class ProfileIn(BaseModel):
    name: Optional[str] = None
    college: Optional[str] = None
    branch: Optional[str] = None
    current_year: Optional[int] = Field(None, ge=1, le=6)
    cgpa: Optional[float] = Field(None, ge=0, le=10)
    tenth_pct: Optional[float] = Field(None, ge=0, le=100)
    twelfth_pct: Optional[float] = Field(None, ge=0, le=100)
    active_backlogs: Optional[int] = Field(None, ge=0)
    skills: Optional[list[str]] = None
    resume_latex: Optional[str] = None


class ProfileOut(ORMModel):
    id: int
    name: Optional[str] = None
    college: Optional[str] = None
    branch: Optional[str] = None
    current_year: Optional[int] = None
    cgpa: Optional[float] = None
    tenth_pct: Optional[float] = None
    twelfth_pct: Optional[float] = None
    active_backlogs: Optional[int] = None
    skills: Optional[list[str]] = None
    resume_url: Optional[str] = None
    resume_parsed: Optional[dict] = None
    resume_latex: Optional[str] = None
    profile_complete: bool = False


# ── Opportunities ─────────────────────────────────────────────────────────
class EligibilityOut(BaseModel):
    status: str
    reasons: list[str] = []
    score: Optional[float] = None


class OpportunityIn(BaseModel):
    company_name: str
    role: Optional[str] = None
    opportunity_type: str = "Other"
    description: Optional[str] = None
    deadline: Optional[date] = None
    salary_stipend: Optional[str] = None
    job_location: Optional[str] = None
    required_skills: list[str] = []
    eligibility_criteria: dict = {}


class OpportunityOut(ORMModel):
    id: int
    company_name: Optional[str] = None
    role: Optional[str] = None
    opportunity_type: str = "Other"
    description: Optional[str] = None
    deadline: Optional[date] = None
    salary_stipend: Optional[str] = None
    job_location: Optional[str] = None
    required_skills: Optional[list[str]] = None
    eligibility_criteria: Optional[dict] = None
    source: str = "manual"
    source_email_id: Optional[str] = None
    created_at: Optional[datetime] = None
    # Enriched per-user fields (not DB columns)
    eligibility: Optional[EligibilityOut] = None
    application_id: Optional[int] = None
    application_status: Optional[str] = None
    # Direct Gmail link to the source email (None for manually-added opportunities)
    email_link: Optional[str] = None


# ── Applications ──────────────────────────────────────────────────────────
class ApplicationCreate(BaseModel):
    opportunity_id: int


class StatusUpdate(BaseModel):
    status: str
    notes: Optional[str] = None


class ApplicationOut(ORMModel):
    id: int
    status: str
    eligibility_status: Optional[str] = None
    eligibility_reasons: Optional[list] = None
    eligibility_score: Optional[float] = None
    cover_letter_url: Optional[str] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    opportunity: OpportunityOut


# ── AI ────────────────────────────────────────────────────────────────────
class ExtractIn(BaseModel):
    subject: str = ""
    body: str


class ClassificationOut(BaseModel):
    label: str
    confidence: float
    method: str


class ExtractOut(BaseModel):
    company_name: Optional[str] = None
    role: Optional[str] = None
    opportunity_type: str = "Other"
    deadline: Optional[str] = None
    salary_stipend: Optional[str] = None
    job_location: Optional[str] = None
    required_skills: list[str] = []
    min_cgpa: Optional[float] = None
    allowed_branches: Optional[list[str]] = None
    allowed_years: Optional[list[int]] = None
    min_tenth: Optional[float] = None
    min_twelfth: Optional[float] = None
    no_backlogs_required: Optional[bool] = None
    summary: Optional[str] = None
    classification: Optional[ClassificationOut] = None


class ResumeAnalysisOut(BaseModel):
    ats_score: int
    matched_keywords: list[str] = []
    missing_keywords: list[str] = []
    skill_gaps: list[str] = []
    suggestions: list[str] = []
    tailored_summary: Optional[str] = None


class CoverLetterOut(BaseModel):
    text: str
    pdf_url: Optional[str] = None


class TailoredResumeOut(BaseModel):
    pdf_url: Optional[str] = None
    highlighted: list[str] = []
    suggestions: list[str] = []
    ats_score: Optional[int] = None
    note: str = ""


class LatexTailorOut(BaseModel):
    latex: str
    changes: list[str] = []
    filename: str = "resume_tailored.tex"
    used_llm: bool = True


class ResearchOut(BaseModel):
    company: str
    overview: str = ""
    tech_stack: str = ""
    interview_tips: str = ""
    hiring_trends: str = ""
    sources: list[str] = []
    cached: bool = False
    generated_at: Optional[str] = None


class CareerAdviceOut(BaseModel):
    summary: str = ""
    target_companies: list[str] = []
    skills_to_learn: list[str] = []
    certifications: list[str] = []
    project_ideas: list[str] = []
    hackathons: list[str] = []


# ── Analytics ─────────────────────────────────────────────────────────────
class AnalyticsDashboardOut(BaseModel):
    stats: dict
    status_counts: dict
    skill_demand: list[dict] = []
    upcoming_deadlines: list[dict] = []


class AnalyticsChartsOut(BaseModel):
    status_pie: Optional[str] = None  # base64 PNG
    skill_gap_bar: Optional[str] = None  # base64 PNG


# ── Announcements ─────────────────────────────────────────────────────────
class AnnouncementOut(ORMModel):
    id: int
    title: str
    body: Optional[str] = None
    created_by: Optional[str] = None
    created_at: Optional[datetime] = None
