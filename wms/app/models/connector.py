"""Tenant connector credentials (encrypted at application level)."""
from __future__ import annotations
import uuid
from sqlalchemy import String, ForeignKey, Boolean, JSON, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, uuidpk, created_at, updated_at


class ConnectorConfig(Base):
    """
    Stores per-tenant connector settings.
    connector_type: "smartup" | "aslbelgisi"
    credentials: encrypted dict (base64 Fernet in production).
    """
    __tablename__ = "connector_configs"

    id: Mapped[uuidpk]
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    connector_type: Mapped[str] = mapped_column(String(50), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # Credentials stored as JSON — encrypt sensitive fields before saving
    # smartup:    {base_url, login, password_enc, project_code, filial_id}
    # aslbelgisi: {api_key_enc, tin, base_url}
    credentials: Mapped[dict] = mapped_column(JSON, nullable=False)
    # Extra settings (timeouts, sync interval, etc.)
    settings: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[created_at]
    updated_at: Mapped[updated_at]

    __table_args__ = (
        UniqueConstraint("tenant_id", "connector_type", name="uq_connector_tenant_type"),
    )
