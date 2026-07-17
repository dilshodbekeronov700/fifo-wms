"""putaway reservations (bron) — two-step reserve/confirm putaway

Revision ID: 0002_putaway_reservations
Revises: 0001_baseline
Create Date: 2026-06-22
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0002_putaway_reservations"
down_revision = "0001_baseline"
branch_labels = None
depends_on = None


reservation_status = sa.Enum(
    "pending", "confirmed", "cancelled", "expired", name="reservationstatus"
)


def upgrade() -> None:
    bind = op.get_bind()
    reservation_status.create(bind, checkfirst=True)

    op.create_table(
        "putaway_reservations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("warehouse_id", sa.Uuid(), sa.ForeignKey("warehouses.id"), nullable=False),
        sa.Column("code", sa.String(length=200), nullable=False),
        sa.Column("package_type", sa.String(length=20), nullable=True),
        sa.Column("product_id", sa.Uuid(), sa.ForeignKey("products.id"), nullable=True),
        sa.Column("batch_id", sa.Uuid(), sa.ForeignKey("batches.id"), nullable=True),
        sa.Column("qty", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("unit_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("location_id", sa.Uuid(), sa.ForeignKey("locations.id"), nullable=False),
        sa.Column("zone_id", sa.Uuid(), sa.ForeignKey("zones.id"), nullable=True),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("reason", sa.String(length=500), nullable=True),
        sa.Column("manual", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("status", reservation_status, nullable=False, server_default="pending"),
        sa.Column("payload", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("reserved_by", sa.Uuid(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("confirmed_by", sa.Uuid(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_putaway_reservations_tenant_id", "putaway_reservations", ["tenant_id"])
    op.create_index("ix_putaway_reservations_warehouse_id", "putaway_reservations", ["warehouse_id"])
    op.create_index("ix_putaway_reservations_code", "putaway_reservations", ["code"])
    op.create_index("ix_putaway_reservations_location_id", "putaway_reservations", ["location_id"])
    op.create_index("ix_putaway_reservations_status", "putaway_reservations", ["status"])
    op.create_index("ix_putaway_reservations_expires_at", "putaway_reservations", ["expires_at"])
    op.create_index("ix_reservation_active_location", "putaway_reservations", ["location_id", "status"])
    op.create_index("ix_reservation_wh_status", "putaway_reservations", ["warehouse_id", "status"])


def downgrade() -> None:
    op.drop_table("putaway_reservations")
    reservation_status.drop(op.get_bind(), checkfirst=True)
