"""Indexes for the hot query paths.

- applications.opportunity_id: FK joins + ON DELETE CASCADE scans.
- opportunities.opportunity_type: the type filter on the list endpoint.
- opportunities.created_at: the default "newest" sort.
- reminders.application_id: reminder scheduling lookups + cascade.

if_not_exists guards databases where create_all already added these (a fresh
no-Alembic boot with the current models, later stamped).

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-02

"""
from __future__ import annotations

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

INDEXES = [
    ("ix_applications_opportunity_id", "applications", ["opportunity_id"]),
    ("ix_opportunities_opportunity_type", "opportunities", ["opportunity_type"]),
    ("ix_opportunities_created_at", "opportunities", ["created_at"]),
    ("ix_reminders_application_id", "reminders", ["application_id"]),
]


def upgrade() -> None:
    for name, table, cols in INDEXES:
        op.create_index(name, table, cols, if_not_exists=True)


def downgrade() -> None:
    for name, table, _ in INDEXES:
        op.drop_index(name, table_name=table, if_exists=True)
