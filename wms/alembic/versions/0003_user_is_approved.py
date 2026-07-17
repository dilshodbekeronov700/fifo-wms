"""user.is_approved — self sign-up approval gate

Revision ID: 0003_user_is_approved
Revises: 0002_putaway_reservations
Create Date: 2026-06-22
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0003_user_is_approved"
down_revision = "0002_putaway_reservations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Existing users are considered approved so nothing breaks; new self sign-ups
    # explicitly insert is_approved=false.
    op.add_column(
        "users",
        sa.Column("is_approved", sa.Boolean(), nullable=False, server_default=sa.true()),
    )


def downgrade() -> None:
    op.drop_column("users", "is_approved")
