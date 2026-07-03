-- PlaceMentor AI — Supabase PostgreSQL schema (single source of truth for the
-- shared relational tables used by BOTH the FastAPI service and the Django
-- admin portal). Run this once in the Supabase SQL editor.
--
-- FastAPI's SQLAlchemy create_all is idempotent (checkfirst) and the Django
-- models are managed=False, so neither ORM fights this schema.

CREATE TABLE IF NOT EXISTS users (
    id                  SERIAL PRIMARY KEY,
    email               VARCHAR(255) UNIQUE NOT NULL,
    password_hash       VARCHAR(255),
    is_admin            BOOLEAN DEFAULT FALSE,
    gmail_access_token  TEXT,
    gmail_refresh_token TEXT,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS student_profiles (
    id              SERIAL PRIMARY KEY,
    user_id         INT UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    name            VARCHAR(255),
    college         VARCHAR(255),
    branch          VARCHAR(100),
    current_year    SMALLINT,
    cgpa            NUMERIC(4,2),
    tenth_pct       NUMERIC(5,2),
    twelfth_pct     NUMERIC(5,2),
    active_backlogs SMALLINT DEFAULT 0,
    skills          JSONB,
    resume_url      TEXT,
    resume_parsed   JSONB,
    resume_latex    TEXT
);

CREATE TABLE IF NOT EXISTS opportunities (
    id                   SERIAL PRIMARY KEY,
    company_name         VARCHAR(255),
    role                 VARCHAR(255),
    opportunity_type     VARCHAR(50) DEFAULT 'Other',
    description          TEXT,
    deadline             DATE,
    salary_stipend       VARCHAR(100),
    job_location         VARCHAR(255),
    required_skills      JSONB,
    eligibility_criteria JSONB,
    source_email_id      VARCHAR(255) UNIQUE,
    source               VARCHAR(20) DEFAULT 'manual',
    created_at           TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS applications (
    id                  SERIAL PRIMARY KEY,
    user_id             INT REFERENCES users(id) ON DELETE CASCADE,
    opportunity_id      INT REFERENCES opportunities(id) ON DELETE CASCADE,
    status              VARCHAR(50) DEFAULT 'Interested',
    eligibility_status  VARCHAR(30),
    eligibility_reasons JSONB,
    eligibility_score   DOUBLE PRECISION,
    cover_letter_url    TEXT,
    notes               TEXT,
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (user_id, opportunity_id)
);

CREATE TABLE IF NOT EXISTS reminders (
    id             SERIAL PRIMARY KEY,
    application_id INT REFERENCES applications(id) ON DELETE CASCADE,
    remind_at      TIMESTAMPTZ,
    reminder_type  VARCHAR(20),
    sent           BOOLEAN DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS announcements (
    id          SERIAL PRIMARY KEY,
    title       VARCHAR(255) NOT NULL,
    body        TEXT,
    created_by  VARCHAR(255),
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_opportunities_deadline ON opportunities (deadline);
CREATE INDEX IF NOT EXISTS idx_opportunities_company ON opportunities (company_name);
CREATE INDEX IF NOT EXISTS idx_applications_user ON applications (user_id);
CREATE INDEX IF NOT EXISTS idx_reminders_due ON reminders (remind_at) WHERE sent = FALSE;

-- Hot-path indexes (Alembic migration 0002 mirrors these):
-- FK joins + cascade scans, the type filter, and the default "newest" sort.
CREATE INDEX IF NOT EXISTS ix_applications_opportunity_id ON applications (opportunity_id);
CREATE INDEX IF NOT EXISTS ix_opportunities_opportunity_type ON opportunities (opportunity_type);
CREATE INDEX IF NOT EXISTS ix_opportunities_created_at ON opportunities (created_at);
CREATE INDEX IF NOT EXISTS ix_reminders_application_id ON reminders (application_id);
