"""Immutable ledger — every stock movement is recorded here, never updated or deleted."""
from __future__ import annotations
import uuid
from enum import Enum as PyEnum
from sqlalchemy import String, ForeignKey, Integer, JSON, Enum as SaEnum, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, uuidpk, created_at


class LedgerAction(str, PyEnum):
    # Receiving
    RECEIPT = "receipt"
    # Putaway
    PUTAWAY = "putaway"
    # Picking / outbound
    PICK = "pick"
    SHIPMENT = "shipment"
    # Internal movement
    MOVE = "move"
    # Return from customer
    RETURN_IN = "return_in"
    # Return to supplier
    RETURN_OUT = "return_out"
    # Inventory adjustment
    INVENTORY_PLUS = "inventory_plus"
    INVENTORY_MINUS = "inventory_minus"
    # Write-off
    WRITEOFF = "writeoff"
    # Booking / unbook (reservation)
    BOOK = "book"
    UNBOOK = "unbook"
    # Status change (block/unblock)
    BLOCK = "block"
    UNBLOCK = "unblock"


class LedgerEntry(Base):
    """
    Append-only journal.  Every row records a quantity delta at a specific location.
    Positive qty_delta = stock IN, negative = stock OUT.
    Current stock is derived by summing ledger entries (or from StockItem cache).
    """

    __tablename__ = "ledger_entries"

    id: Mapped[uuidpk]
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    warehouse_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("warehouses.id"), nullable=False)
    action: Mapped[LedgerAction] = mapped_column(SaEnum(LedgerAction), nullable=False)

    # What moved
    product_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("products.id"))
    batch_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("batches.id"))
    marking_code: Mapped[str | None] = mapped_column(String(200))  # exact DataMatrix KIZ value

    # From / To locations (null for external origin/destination)
    from_location_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("locations.id"))
    to_location_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("locations.id"))

    # Quantity in base unit (units/boxes depending on product UOM config)
    qty_delta: Mapped[int] = mapped_column(Integer, nullable=False)

    # Who / Why
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    document_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("documents.id"))
    reason: Mapped[str | None] = mapped_column(String(500))
    extra: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    # created_at = event timestamp; immutable
    created_at: Mapped[created_at]

    __table_args__ = (
        Index("ix_ledger_tenant_warehouse", "tenant_id", "warehouse_id"),
        Index("ix_ledger_product_batch", "product_id", "batch_id"),
        Index("ix_ledger_location_from", "from_location_id"),
        Index("ix_ledger_location_to", "to_location_id"),
        Index("ix_ledger_created_at", "created_at"),
    )
