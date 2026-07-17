"""Tenant management — super-admin only."""
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import ActiveUser, get_db
from app.core.security import hash_password
from app.models.auth import Role, User
from app.models.tenant import Tenant
from app.models.warehouse import Warehouse
from app.schemas.tenant import (
    TenantCreate, TenantOut, TenantProvision, TenantSettings, TenantUpdate,
)

router = APIRouter(prefix="/tenants", tags=["tenants"])
DB = Annotated[AsyncSession, Depends(get_db)]


def _require_superadmin(user: ActiveUser) -> None:
    if not user.is_superadmin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Super-admin only")


@router.post("/", response_model=TenantOut, status_code=201)
async def create_tenant(body: TenantCreate, user: ActiveUser, db: DB):
    _require_superadmin(user)
    existing = await db.execute(select(Tenant).where(Tenant.slug == body.slug))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Slug already taken")
    tenant = Tenant(name=body.name, slug=body.slug, settings=body.settings)
    db.add(tenant)
    await db.commit()
    await db.refresh(tenant)
    return tenant


@router.get("/", response_model=list[TenantOut])
async def list_tenants(user: ActiveUser, db: DB):
    _require_superadmin(user)
    result = await db.execute(select(Tenant).order_by(Tenant.name))
    return result.scalars().all()


@router.get("/{tenant_id}", response_model=TenantOut)
async def get_tenant(tenant_id: uuid.UUID, user: ActiveUser, db: DB):
    if not user.is_superadmin and user.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one_or_none()
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return tenant


@router.patch("/{tenant_id}", response_model=TenantOut)
async def update_tenant(tenant_id: uuid.UUID, body: TenantUpdate, user: ActiveUser, db: DB):
    _require_superadmin(user)
    tenant = (await db.execute(select(Tenant).where(Tenant.id == tenant_id))).scalar_one_or_none()
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    if body.name is not None:
        tenant.name = body.name
    if body.is_active is not None:
        tenant.is_active = body.is_active
    await db.commit()
    await db.refresh(tenant)
    return tenant


@router.get("/{tenant_id}/settings")
async def get_settings(tenant_id: uuid.UUID, user: ActiveUser, db: DB) -> dict:
    if not user.is_superadmin and user.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    tenant = (await db.execute(select(Tenant).where(Tenant.id == tenant_id))).scalar_one_or_none()
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return tenant.settings or {}


@router.patch("/{tenant_id}/settings")
async def update_settings(
    tenant_id: uuid.UUID, body: TenantSettings, user: ActiveUser, db: DB
) -> dict:
    # Tenant-admin may edit their own tenant; super-admin any.
    if not user.is_superadmin and user.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    tenant = (await db.execute(select(Tenant).where(Tenant.id == tenant_id))).scalar_one_or_none()
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    merged = dict(tenant.settings or {})
    for k, v in body.model_dump(exclude_none=True).items():
        merged[k] = v
    tenant.settings = merged
    await db.commit()
    return merged


@router.post("/provision", status_code=201)
async def provision_tenant(body: TenantProvision, user: ActiveUser, db: DB) -> dict:
    """One-shot onboarding: tenant + first admin user + optional warehouse."""
    _require_superadmin(user)
    if (await db.execute(select(Tenant).where(Tenant.slug == body.slug))).scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Slug already taken")
    if (await db.execute(select(User).where(User.email == body.admin_email))).scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Admin email already exists")

    tenant = Tenant(name=body.name, slug=body.slug, settings={"locale": body.locale})
    db.add(tenant)
    await db.flush()

    admin = User(
        tenant_id=tenant.id,
        email=body.admin_email,
        full_name=body.admin_full_name,
        hashed_password=hash_password(body.admin_password),
        is_active=True,
    )
    # Attach the system "tenant_admin" role if seeded.
    role = (await db.execute(
        select(Role).where(Role.name == "tenant_admin")
    )).scalar_one_or_none()
    if role is not None:
        admin.roles.append(role)
    db.add(admin)

    warehouse_id = None
    if body.warehouse_name:
        wh = Warehouse(tenant_id=tenant.id, name=body.warehouse_name)
        db.add(wh)
        await db.flush()
        warehouse_id = str(wh.id)

    await db.commit()
    return {
        "tenant_id": str(tenant.id),
        "admin_email": body.admin_email,
        "warehouse_id": warehouse_id,
        "status": "provisioned",
    }
