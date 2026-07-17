"""ExceptionEvent — warehouse exceptions requiring attention/escalation (TZ §7.13).

Examples: unknown code, ownership mismatch (forbiddenCode), wrong location scan,
damaged goods, order-line mismatch. Each is logged, optionally assigned to a
shift lead, and resolved with a reason.
"""
from __future__ import annotations

import uuid
from enum import Enum as PyEnum

from sqlalchemy import String, ForeignKey, JSON, Enum as SaEnum, Integer, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, uuidpk, created_at, updated_at


class ExceptionType(str, PyEnum):
    UNKNOWN_CODE = "unknown_code"
    FORBIDDEN_OWNER = "forbidden_owner"
    WRONG_LOCATION = "wrong_location"
    DAMAGED = "damaged"
    ORDER_MISMATCH = "order_mismatch"
    PRODUCT_NOT_MAPPED = "product_not_mapped"
    OTHER = "other"


class ExceptionStatus(str, PyEnum):
    OPEN = "open"
    ACK = "acknowledged"
    RESOLVED = "resolved"


class ExceptionEvent(Base):
    __tablename__ = "exception_events"

    id: Mapped[uuidpk]
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    warehouse_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("warehouses.id"))
    exc_type: Mapped[ExceptionType] = mapped_column(SaEnum(ExceptionType), nullable=False)
    status: Mapped[ExceptionStatus] = mapped_column(
        SaEnum(ExceptionStatus), default=ExceptionStatus.OPEN, nullable=False
    )
    severity: Mapped[int] = mapped_column(Integer, default=50, nullable=False)  # 0..100
    marking_code: Mapped[str | None] = mapped_column(String(200))
    message: Mapped[str | None] = mapped_column(String(500))
    detail: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    assigned_to: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    resolution: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[created_at]
    updated_at: Mapped[updated_at]

    __table_args__ = (
        Index("ix_exception_tenant_status", "tenant_id", "status"),
    )
