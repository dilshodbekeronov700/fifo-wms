"""Product, Batch, MarkingCode, StockItem, Document, OutboxMessage."""
from __future__ import annotations
import uuid
from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import (
    String, ForeignKey, Boolean, Integer, Float, JSON, Enum as SaEnum, UniqueConstraint, Index, Text, CheckConstraint, DateTime, text
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, uuidpk, created_at, updated_at


class AbcClass(str, PyEnum):
    A = "A"
    B = "B"
    C = "C"


class PackageType(str, PyEnum):
    UNIT = "UNIT"
    GROUP = "GROUP"        # latok / box
    BOX_LV_1 = "BOX_LV_1"  # pallet level 1 (SSCC)
    BOX_LV_2 = "BOX_LV_2"  # pallet level 2
    ACC = "ACC"            # aggregated import code container
    SET = "SET"            # set / komplekt


class MarkingCodeStatus(str, PyEnum):
    RECEIVED = "RECEIVED"
    APPLIED = "APPLIED"
    INTRODUCED = "INTRODUCED"
    WITHDRAWN = "WITHDRAWN"
    WRITTEN_OFF = "WRITTEN_OFF"


class StockStatus(str, PyEnum):
    AVAILABLE = "available"
    BOOKED = "booked"
    BLOCKED = "blocked"


class DocumentType(str, PyEnum):
    RECEIPT = "receipt"
    SHIPMENT = "shipment"
    MOVEMENT = "movement"
    INVENTORY = "inventory"
    WRITEOFF = "writeoff"
    RETURN = "return"


class DocumentStatus(str, PyEnum):
    DRAFT = "draft"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class OutboxStatus(str, PyEnum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"


# ---------------------------------------------------------------------------
# Product (SKU)
# ---------------------------------------------------------------------------
class Product(Base):
    __tablename__ = "products"

    id: Mapped[uuidpk]
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    smartup_product_code: Mapped[str | None] = mapped_column(String(100))
    gtin: Mapped[str | None] = mapped_column(String(20))
    name: Mapped[dict] = mapped_column(JSON, nullable=False)  # {"ru": "...", "uz": "..."}
    uom: Mapped[str] = mapped_column(String(20), default="unit", nullable=False)
    units_per_box: Mapped[int | None] = mapped_column(Integer)
    boxes_per_pallet: Mapped[int | None] = mapped_column(Integer)
    abc_class: Mapped[AbcClass | None] = mapped_column(SaEnum(AbcClass))
    # Safety-stock / replenishment thresholds (pick-face bo'yicha, boxes/GROUP).
    # min_stock — shu darajaga tushsa to'ldirish (replenishment) ishga tushadi.
    # max_stock — to'ldirishda shu darajagacha ko'tariladi (target). NULL = o'chiq.
    min_stock: Mapped[int | None] = mapped_column(Integer)
    max_stock: Mapped[int | None] = mapped_column(Integer)
    # Free-form admin tag used for putaway routing (e.g. "19L", "0.5L").
    category: Mapped[str | None] = mapped_column(String(50), index=True)
    weight_kg: Mapped[float | None] = mapped_column(Float)
    volume_m3: Mapped[float | None] = mapped_column(Float)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[created_at]
    updated_at: Mapped[updated_at]

    __table_args__ = (
        UniqueConstraint("tenant_id", "smartup_product_code", name="uq_product_tenant_smartup"),
        # GTIN faol mahsulotlar ichida tenant bo'yicha unikal (NULL va nofaollar bundan mustasno).
        Index(
            "uq_product_tenant_gtin_active",
            "tenant_id", "gtin",
            unique=True,
            postgresql_where=text("gtin IS NOT NULL AND is_active"),
        ),
    )

    batches: Mapped[list["Batch"]] = relationship(back_populates="product")


# ---------------------------------------------------------------------------
# Batch (lot / partiya)
# ---------------------------------------------------------------------------
class BatchStatus(str, PyEnum):
    AVAILABLE = "available"
    BLOCKED = "blocked"
    QUARANTINE = "quarantine"
    EXPIRED = "expired"


class Batch(Base):
    __tablename__ = "batches"

    id: Mapped[uuidpk]
    product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("products.id"), nullable=False, index=True)
    lot_number: Mapped[str | None] = mapped_column(String(100))
    production_date: Mapped[str | None] = mapped_column(String(20))   # ISO date string
    expiry_date: Mapped[str | None] = mapped_column(String(20))
    status: Mapped[BatchStatus] = mapped_column(
        SaEnum(BatchStatus), default=BatchStatus.AVAILABLE, nullable=False
    )
    created_at: Mapped[created_at]

    product: Mapped["Product"] = relationship(back_populates="batches")


# ---------------------------------------------------------------------------
# MarkingCode (DataMatrix KIZ)
# ---------------------------------------------------------------------------
class MarkingCode(Base):
    __tablename__ = "marking_codes"

    id: Mapped[uuidpk]
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(200), nullable=False, unique=True, index=True)
    gtin: Mapped[str | None] = mapped_column(String(20))
    package_type: Mapped[PackageType] = mapped_column(SaEnum(PackageType), nullable=False)
    parent_code: Mapped[str | None] = mapped_column(String(200), index=True)
    # Asl Belgisi 9.2 (private_codes) boyitishdan — FEFO/ma'lumot uchun.
    expiry_date: Mapped[str | None] = mapped_column(String(20))
    batch_number: Mapped[str | None] = mapped_column(String(60))
    production_date: Mapped[str | None] = mapped_column(String(20))
    mc_status: Mapped[MarkingCodeStatus] = mapped_column(
        SaEnum(MarkingCodeStatus), default=MarkingCodeStatus.RECEIVED, nullable=False
    )
    product_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("products.id"))
    batch_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("batches.id"))
    location_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("locations.id"))
    created_at: Mapped[created_at]
    updated_at: Mapped[updated_at]


# ---------------------------------------------------------------------------
# StockItem — denormalized cache (source of truth = LedgerEntry sums)
# ---------------------------------------------------------------------------
class StockItem(Base):
    __tablename__ = "stock_items"

    id: Mapped[uuidpk]
    warehouse_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("warehouses.id"), nullable=False)
    location_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("locations.id"), nullable=False)
    product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("products.id"), nullable=False)
    batch_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("batches.id"))
    qty: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    qty_booked: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[StockStatus] = mapped_column(
        SaEnum(StockStatus), default=StockStatus.AVAILABLE, nullable=False
    )
    pallet_open: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    updated_at: Mapped[updated_at]

    __table_args__ = (
        UniqueConstraint("location_id", "product_id", "batch_id", name="uq_stock_location_product_batch"),
        Index("ix_stock_warehouse_product", "warehouse_id", "product_id"),
        CheckConstraint("qty >= 0", name="ck_stock_qty_nonneg"),
        CheckConstraint("qty_booked >= 0", name="ck_stock_booked_nonneg"),
        CheckConstraint("qty_booked <= qty", name="ck_stock_booked_le_qty"),
    )


# ---------------------------------------------------------------------------
# Document (header for receipts, shipments, etc.)
# ---------------------------------------------------------------------------
class Document(Base):
    __tablename__ = "documents"

    id: Mapped[uuidpk]
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    warehouse_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("warehouses.id"), nullable=False)
    doc_type: Mapped[DocumentType] = mapped_column(SaEnum(DocumentType), nullable=False)
    status: Mapped[DocumentStatus] = mapped_column(
        SaEnum(DocumentStatus), default=DocumentStatus.DRAFT, nullable=False
    )
    external_id: Mapped[str | None] = mapped_column(String(200), index=True)   # Smartup deal/order id
    smartup_id: Mapped[str | None] = mapped_column(String(200))
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    notes: Mapped[str | None] = mapped_column(Text)
    extra: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[created_at]
    updated_at: Mapped[updated_at]


# ---------------------------------------------------------------------------
# OutboxMessage — reliable integration delivery
# ---------------------------------------------------------------------------
class OutboxMessage(Base):
    __tablename__ = "outbox_messages"

    id: Mapped[uuidpk]
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    connector: Mapped[str] = mapped_column(String(50), nullable=False)  # "smartup" | "aslbelgisi"
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    status: Mapped[OutboxStatus] = mapped_column(
        SaEnum(OutboxStatus), default=OutboxStatus.PENDING, nullable=False
    )
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_error: Mapped[str | None] = mapped_column(Text)
    # Backoff scheduling — message is only picked up when next_retry_at <= now
    next_retry_at: Mapped["datetime | None"] = mapped_column(DateTime(timezone=True))
    # Stage-2 async result polling (Asl Belgisi docs): returned documentId + its state
    result_doc_id: Mapped[str | None] = mapped_column(String(200))
    result_status: Mapped[str | None] = mapped_column(String(50))  # SUCCESS/WARNING/ERROR
    created_at: Mapped[created_at]
    updated_at: Mapped[updated_at]

    __table_args__ = (
        Index("ix_outbox_status_created", "status", "created_at"),
        Index("ix_outbox_status_retry", "status", "next_retry_at"),
    )
