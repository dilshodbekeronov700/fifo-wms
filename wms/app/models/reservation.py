"""
Putaway reservation (bron) — the two-step "reserve then confirm-by-scan" flow.

World-class WMS practice: a directed-putaway suggestion is never auto-committed.
The operator first *reserves* a slot (so no two operators race for the same
location and the slotting engine stops offering it), then physically walks to the
rack and *confirms* by scanning the location's QR / DataMatrix barcode. Only the
confirm step writes the PUTAWAY ledger entry and moves stock.

Lifecycle:
    PENDING    — slot reserved for this transport code; capacity is held.
    CONFIRMED  — operator scanned the location barcode → stock placed (terminal).
    CANCELLED  — operator released the reservation (terminal).
    EXPIRED    — TTL elapsed without confirmation; capacity auto-released (terminal).

A reservation captures the *full resolved snapshot* from Asl Belgisi (children,
gtin, dates, counts) in `payload` so the confirm step needs no second network
round-trip and the map/cell view can show the aggregation tree.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import (
    String, ForeignKey, Integer, Float, JSON, Enum as SaEnum, Index, DateTime,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, uuidpk, created_at, updated_at


class ReservationStatus(str, PyEnum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class PutawayReservation(Base):
    """A held slot for a scanned transport/pallet code awaiting physical placement."""

    __tablename__ = "putaway_reservations"

    id: Mapped[uuidpk]
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    warehouse_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("warehouses.id"), nullable=False, index=True)

    # What is being put away
    code: Mapped[str] = mapped_column(String(200), nullable=False, index=True)  # transport/pallet code
    package_type: Mapped[str | None] = mapped_column(String(20))
    product_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("products.id"))
    batch_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("batches.id"))
    qty: Mapped[int] = mapped_column(Integer, default=1, nullable=False)        # boxes (GROUP)
    unit_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # bottles

    # Where it is reserved
    location_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("locations.id"), nullable=False, index=True)
    zone_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("zones.id"))

    # Decision provenance (why this slot) — full factor breakdown for transparency
    score: Mapped[float | None] = mapped_column(Float)
    reason: Mapped[str | None] = mapped_column(String(500))
    manual: Mapped[bool] = mapped_column(default=False, nullable=False)  # operator-overridden slot

    status: Mapped[ReservationStatus] = mapped_column(
        SaEnum(ReservationStatus), default=ReservationStatus.PENDING, nullable=False, index=True
    )

    # Resolved Asl Belgisi snapshot (children tree, gtin, dates, counting_method, factor breakdown…)
    payload: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    reserved_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    confirmed_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    created_at: Mapped[created_at]
    updated_at: Mapped[updated_at]

    __table_args__ = (
        Index("ix_reservation_active_location", "location_id", "status"),
        Index("ix_reservation_wh_status", "warehouse_id", "status"),
    )
