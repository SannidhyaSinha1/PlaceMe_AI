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
    is_admin: bool = False
    gmail_connected: bool = False
    profile_complete: bool = False
    created_at: datetime | None = None


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ── Profile ───────────────────────────────────────────────────────────────
class ProfileIn(BaseModel):
    # String caps match the DB column sizes so writes can't fail downstream.
    name: str | None = Field(None, max_length=255)
    college: str | None = Field(None, max_length=255)
    branch: str | None = Field(None, max_length=100)
    current_year: int | None = Field(None, ge=1, le=6)
    cgpa: float | None = Field(None, ge=0, le=10)
    tenth_pct: float | None = Field(None, ge=0, le=100)
    twelfth_pct: float | None = Field(None, ge=0, le=100)
    active_backlogs: int | None = Field(None, ge=0, le=50)
    skills: list[str] | None = Field(None, max_length=100)
    resume_latex: str | None = Field(None, max_length=200_000)


class ProfileOut(ORMModel):
    id: int
    name: str | None = None
    college: str | None = None
    branch: str | None = None
    current_year: int | None = None
    cgpa: float | None = None
    tenth_pct: float | None = None
    twelfth_pct: float | None = None
    active_backlogs: int | None = None
    skills: list[str] | None = None
    resume_url: str | None = None
    resume_parsed: dict | None = None
    resume_latex: str | None = None
    profile_complete: bool = False


# ── Opportunities ─────────────────────────────────────────────────────────
class EligibilityOut(BaseModel):
    status: str
    reasons: list[str] = []
    score: float | None = None


class OpportunityIn(BaseModel):
    company_name: str
    role: str | None = None
    opportunity_type: str = "Other"
    description: str | None = None
    deadline: date | None = None
    salary_stipend: str | None = None
    job_location: str | None = None
    required_skills: list[str] = []
    eligibility_criteria: dict = {}


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
    source: str = "manual"
    source_email_id: str | None = None
    created_at: datetime | None = None
    # Enriched per-user fields (not DB columns)
    eligibility: EligibilityOut | None = None
    application_id: int | None = None
    application_status: str | None = None
    # Direct Gmail link to the source email (None for manually-added opportunities)
    email_link: str | None = None


# ── Applications ──────────────────────────────────────────────────────────
class ApplicationCreate(BaseModel):
    opportunity_id: int


class StatusUpdate(BaseModel):
    status: str = Field(max_length=50)
    notes: str | None = Field(None, max_length=5_000)


class ApplicationOut(ORMModel):
    id: int
    status: str
    eligibility_status: str | None = None
    eligibility_reasons: list | None = None
    eligibility_score: float | None = None
    cover_letter_url: str | None = None
    notes: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    opportunity: OpportunityOut


# ── AI ────────────────────────────────────────────────────────────────────
class ExtractIn(BaseModel):
    subject: str = Field("", max_length=1_000)
    body: str = Field(max_length=50_000)


class ClassificationOut(BaseModel):
    label: str
    confidence: float
    method: str


class ExtractOut(BaseModel):
    company_name: str | None = None
    role: str | None = None
    opportunity_type: str = "Other"
    deadline: str | None = None
    salary_stipend: str | None = None
    job_location: str | None = None
    required_skills: list[str] = []
    min_cgpa: float | None = None
    allowed_branches: list[str] | None = None
    allowed_years: list[int] | None = None
    min_tenth: float | None = None
    min_twelfth: float | None = None
    no_backlogs_required: bool | None = None
    summary: str | None = None
    classification: ClassificationOut | None = None


class ResumeAnalysisOut(BaseModel):
    ats_score: int
    matched_keywords: list[str] = []
    missing_keywords: list[str] = []
    skill_gaps: list[str] = []
    suggestions: list[str] = []
    tailored_summary: str | None = None


class CoverLetterOut(BaseModel):
    text: str
    pdf_url: str | None = None


class TailoredResumeOut(BaseModel):
    pdf_url: str | None = None
    highlighted: list[str] = []
    suggestions: list[str] = []
    ats_score: int | None = None
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
    generated_at: str | None = None


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
    status_pie: str | None = None  # base64 PNG
    skill_gap_bar: str | None = None  # base64 PNG


# ── Announcements ─────────────────────────────────────────────────────────
class AnnouncementOut(ORMModel):
    id: int
    title: str
    body: str | None = None
    created_by: str | None = None
    created_at: datetime | None = None
