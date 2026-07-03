"""Baseline: the schema as created by SQLAlchemy create_all before Alembic.

Pre-Alembic databases are stamped with this revision at boot instead of
running it (see fastapi_app.core.database.init_models).

Revision ID: 0001
Revises:
Create Date: 2026-07-02

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

# JSONB on Postgres, plain JSON on the SQLite dev fallback (mirrors sql_models).
JsonCol = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("is_admin", sa.Boolean(), nullable=False),
        sa.Column("gmail_access_token", sa.Text(), nullable=True),
        sa.Column("gmail_refresh_token", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True
        ),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "student_profiles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("name", sa.String(255), nullable=True),
        sa.Column("college", sa.String(255), nullable=True),
        sa.Column("branch", sa.String(100), nullable=True),
        sa.Column("current_year", sa.SmallInteger(), nullable=True),
        sa.Column("cgpa", sa.Numeric(4, 2), nullable=True),
        sa.Column("tenth_pct", sa.Numeric(5, 2), nullable=True),
        sa.Column("twelfth_pct", sa.Numeric(5, 2), nullable=True),
        sa.Column("active_backlogs", sa.SmallInteger(), nullable=True),
        sa.Column("skills", JsonCol, nullable=True),
        sa.Column("resume_url", sa.Text(), nullable=True),
        sa.Column("resume_parsed", JsonCol, nullable=True),
        sa.Column("resume_latex", sa.Text(), nullable=True),
    )

    op.create_table(
        "opportunities",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_name", sa.String(255), nullable=True),
        sa.Column("role", sa.String(255), nullable=True),
        sa.Column("opportunity_type", sa.String(50), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("deadline", sa.Date(), nullable=True),
        sa.Column("salary_stipend", sa.String(100), nullable=True),
        sa.Column("job_location", sa.String(255), nullable=True),
        sa.Column("required_skills", JsonCol, nullable=True),
        sa.Column("eligibility_criteria", JsonCol, nullable=True),
        sa.Column("source_email_id", sa.String(255), nullable=True, unique=True),
        sa.Column("source", sa.String(20), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True
        ),
    )
    op.create_index("ix_opportunities_company_name", "opportunities", ["company_name"])
    op.create_index("ix_opportunities_deadline", "opportunities", ["deadline"])

    op.create_table(
        "applications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "opportunity_id",
            sa.Integer(),
            sa.ForeignKey("opportunities.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("eligibility_status", sa.String(30), nullable=True),
        sa.Column("eligibility_reasons", JsonCol, nullable=True),
        sa.Column("eligibility_score", sa.Float(), nullable=True),
        sa.Column("cover_letter_url", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True
        ),
        sa.UniqueConstraint("user_id", "opportunity_id", name="uq_user_opportunity"),
    )

    op.create_table(
        "reminders",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "application_id",
            sa.Integer(),
            sa.ForeignKey("applications.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("remind_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reminder_type", sa.String(20), nullable=False),
        sa.Column("sent", sa.Boolean(), nullable=False),
    )
    op.create_index("ix_reminders_remind_at", "reminders", ["remind_at"])

    op.create_table(
        "announcements",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("created_by", sa.String(255), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True
        ),
    )


def downgrade() -> None:
    for table in ("announcements", "reminders", "applications", "opportunities",
                  "student_profiles", "users"):
        op.drop_table(table)
