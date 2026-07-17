"""User, Role, Permission — RBAC model."""
from __future__ import annotations
import uuid
from datetime import datetime

from sqlalchemy import (
    String, Boolean, ForeignKey, Table, Column, UniqueConstraint, JSON,
    DateTime, Integer,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, uuidpk, created_at, updated_at


# Many-to-many: user ↔ role (per tenant)
user_roles = Table(
    "user_roles",
    Base.metadata,
    Column("user_id", ForeignKey("users.id"), primary_key=True),
    Column("role_id", ForeignKey("roles.id"), primary_key=True),
)

# Many-to-many: role ↔ permission
role_permissions = Table(
    "role_permissions",
    Base.metadata,
    Column("role_id", ForeignKey("roles.id"), primary_key=True),
    Column("permission_id", ForeignKey("permissions.id"), primary_key=True),
)


class Permission(Base):
    """Atomic capability: resource + action, e.g. 'location:create'."""

    __tablename__ = "permissions"

    id: Mapped[uuidpk]
    resource: Mapped[str] = mapped_column(String(100), nullable=False)
    action: Mapped[str] = mapped_column(String(50), nullable=False)  # view/create/update/approve/delete
    description: Mapped[str | None] = mapped_column(String(300))

    __table_args__ = (UniqueConstraint("resource", "action", name="uq_permission_resource_action"),)

    roles: Mapped[list["Role"]] = relationship(secondary=role_permissions, back_populates="permissions")


class Role(Base):
    __tablename__ = "roles"

    id: Mapped[uuidpk]
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("tenants.id"), nullable=True, index=True
    )  # None = platform-level role
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)  # built-in, not editable
    created_at: Mapped[created_at]

    permissions: Mapped[list["Permission"]] = relationship(
        secondary=role_permissions, back_populates="roles"
    )
    users: Mapped[list["User"]] = relationship(secondary=user_roles, back_populates="roles")


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuidpk]
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("tenants.id"), nullable=True, index=True
    )  # None = super-admin (platform level)
    email: Mapped[str] = mapped_column(String(254), unique=True, nullable=False, index=True)
    phone: Mapped[str | None] = mapped_column(String(30), unique=True)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(512), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # Self sign-up approval gate. Provisioned/seeded users are approved; users who
    # self-register start unapproved and cannot log in until an admin approves.
    is_approved: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_superadmin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # Data scope: which warehouses/zones this user can access (empty = all in tenant)
    warehouse_scope: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    # Brute-force protection
    failed_login_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[created_at]
    updated_at: Mapped[updated_at]

    tenant: Mapped["Tenant | None"] = relationship(back_populates="users")
    roles: Mapped[list["Role"]] = relationship(secondary=user_roles, back_populates="users")


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[uuidpk]
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    token_hash: Mapped[str] = mapped_column(String(512), nullable=False, unique=True)
    is_revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[created_at]
    # expires_at stored as UTC timestamp in JWT payload; DB row kept for revocation checks
