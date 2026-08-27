"""Baseline: users (Gmail token holders) + opportunities (parsed emails).

Pre-Alembic databases are stamped with this revision at boot instead of
running it (see fastapi_app.core.database.init_models).

Revision ID: 0001
Revises:
Create Date: 2026-08-27

"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
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
        sa.Column("gmail_access_token", sa.Text(), nullable=True),
        sa.Column("gmail_refresh_token", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True
        ),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

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
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True
        ),
    )
    op.create_index("ix_opportunities_company_name", "opportunities", ["company_name"])
    # The type filter and the default "newest" sort on the list endpoint.
    op.create_index("ix_opportunities_opportunity_type", "opportunities", ["opportunity_type"])
    op.create_index("ix_opportunities_deadline", "opportunities", ["deadline"])
    op.create_index("ix_opportunities_created_at", "opportunities", ["created_at"])


def downgrade() -> None:
    op.drop_table("opportunities")
    op.drop_table("users")
