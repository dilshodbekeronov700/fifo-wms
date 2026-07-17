"""Slotting admin config: zone putaway-rules editor + slotting weights.

UI-driven (admin) configuration of:
  - per-zone `putaway_rules` (zone acceptance) — tenant-scoped via Zone->Warehouse
  - tenant-wide slotting `weights` — stored in Tenant.settings["slotting_weights"]
    and merged over slotting.DEFAULT_WEIGHTS at scoring time.
"""
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import attributes

from app.core.deps import ActiveUser, ensure_warehouse_access, get_db, require_permission
from app.models.tenant import Tenant
from app.models.warehouse import Warehouse, Zone
from app.services.slotting import DEFAULT_WEIGHTS, load_weights

router = APIRouter(prefix="/slotting", tags=["slotting"])
DB = Annotated[AsyncSession, Depends(get_db)]


# ─── Schemas ──────────────────────────────────────────────────────────────────

class ZoneRulesUpdate(BaseModel):
    putaway_rules: dict = Field(default_factory=dict)


class ZoneRulesOut(BaseModel):
    zone_id: uuid.UUID
    putaway_rules: dict


class WeightsUpdate(BaseModel):
    weights: dict[str, float] = Field(default_factory=dict)


class WeightsOut(BaseModel):
    weights: dict[str, float]
    defaults: dict[str, float]


# ─── Zone putaway-rules editor ─────────────────────────────────────────────────

@router.put(
    "/zones/{zone_id}/rules",
    response_model=ZoneRulesOut,
    dependencies=[require_permission("zone", "update")],
)
async def update_zone_rules(
    zone_id: uuid.UUID, body: ZoneRulesUpdate, user: ActiveUser, db: DB
):
    if user.tenant_id is None and not user.is_superadmin:
        raise HTTPException(status_code=403, detail="No tenant context")

    # Validate zone belongs to the caller's tenant (Zone -> Warehouse.tenant_id).
    row = (await db.execute(
        select(Zone, Warehouse)
        .join(Warehouse, Warehouse.id == Zone.warehouse_id)
        .where(Zone.id == zone_id)
    )).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Zone not found")
    zone, warehouse = row
    if not user.is_superadmin and warehouse.tenant_id != user.tenant_id:
        raise HTTPException(status_code=404, detail="Zone not found")

    zone.putaway_rules = body.putaway_rules or {}
    await db.commit()
    await db.refresh(zone)
    return ZoneRulesOut(zone_id=zone.id, putaway_rules=zone.putaway_rules or {})


# ─── Slotting weights config ────────────────────────────────────────────────────

@router.get(
    "/weights",
    response_model=WeightsOut,
    dependencies=[require_permission("slotting", "view")],
)
async def get_slotting_weights(
    user: ActiveUser,
    db: DB,
    warehouse_id: Annotated[uuid.UUID, Query()],
):
    # Resolve tenant via the warehouse (also enforces tenant/scope access).
    wh = await ensure_warehouse_access(db, user, warehouse_id)
    tenant = await db.get(Tenant, wh.tenant_id)
    settings = tenant.settings if tenant else None
    return WeightsOut(weights=load_weights(settings), defaults=dict(DEFAULT_WEIGHTS))


@router.put(
    "/weights",
    response_model=WeightsOut,
    dependencies=[require_permission("slotting", "update")],
)
async def update_slotting_weights(body: WeightsUpdate, user: ActiveUser, db: DB):
    if user.tenant_id is None:
        raise HTTPException(status_code=403, detail="No tenant context")

    tenant = await db.get(Tenant, user.tenant_id)
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")

    # Only persist known weight keys (numeric); keep DEFAULT_WEIGHTS as the schema.
    clean = {
        k: float(v)
        for k, v in (body.weights or {}).items()
        if k in DEFAULT_WEIGHTS and isinstance(v, (int, float))
    }
    settings = dict(tenant.settings or {})
    settings["slotting_weights"] = clean
    tenant.settings = settings
    # JSON column mutation tracking (assignment above already replaces the dict,
    # but flag explicitly to be safe across SQLAlchemy mutable configs).
    attributes.flag_modified(tenant, "settings")
    await db.commit()
    await db.refresh(tenant)
    return WeightsOut(weights=load_weights(tenant.settings), defaults=dict(DEFAULT_WEIGHTS))
