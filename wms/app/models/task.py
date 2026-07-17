"""Operator tasks (putaway, pick, replenish, count)."""
from __future__ import annotations
import uuid
from enum import Enum as PyEnum
from sqlalchemy import ForeignKey, JSON, Enum as SaEnum, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, uuidpk, created_at, updated_at


class TaskType(str, PyEnum):
    PUTAWAY = "putaway"
    PICK = "pick"
    REPLENISH = "replenish"
    COUNT = "count"
    MOVE = "move"


class TaskStatus(str, PyEnum):
    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[uuidpk]
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    warehouse_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("warehouses.id"), nullable=False)
    task_type: Mapped[TaskType] = mapped_column(SaEnum(TaskType), nullable=False)
    status: Mapped[TaskStatus] = mapped_column(
        SaEnum(TaskStatus), default=TaskStatus.PENDING, nullable=False
    )
    priority: Mapped[int] = mapped_column(Integer, default=50, nullable=False)  # 0=low, 100=urgent
    assigned_to: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    document_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("documents.id"))

    # Task payload: varies by type
    # putaway: {product_id, batch_id, marking_code, qty, suggested_location_id, ...}
    # pick: {order_line_id, product_id, qty, from_location_id, ...}
    payload: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    created_at: Mapped[created_at]
    updated_at: Mapped[updated_at]
