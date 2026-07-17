"""Faza C — safety-stock (min/max) on products for replenishment

Revision ID: 0004_faza_c_safety_stock
Revises: 0003_user_is_approved
Create Date: 2026-07-17
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0004_faza_c_safety_stock"
down_revision = "0003_user_is_approved"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("products", sa.Column("min_stock", sa.Integer(), nullable=True))
    op.add_column("products", sa.Column("max_stock", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("products", "max_stock")
    op.drop_column("products", "min_stock")
