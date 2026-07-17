"""AuditLog — who did what, when, to which resource (TZ §4.2 / §6).

Distinct from LedgerEntry (which records *stock* movements). AuditLog records
access and configuration/security events: logins, RBAC changes, connector edits,
document approvals, etc.
"""
from __future__ import annotations

import uuid
from sqlalchemy import String, ForeignKey, JSON, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, uuidpk, created_at


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[uuidpk]
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("tenants.id"), index=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(100), nullable=False)   # login/create/update/delete/...
    resource: Mapped[str] = mapped_column(String(100), nullable=False)  # user/connector/document/...
    resource_id: Mapped[str | None] = mapped_column(String(100))
    ip: Mapped[str | None] = mapped_column(String(64))
    request_id: Mapped[str | None] = mapped_column(String(64))
    # old/new values, extra context
    detail: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[created_at]

    __table_args__ = (
        Index("ix_audit_tenant_created", "tenant_id", "created_at"),
        Index("ix_audit_resource", "resource", "resource_id"),
    )
