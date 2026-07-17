"""
Billing / tariff + SLA (TZ §14 — SaaS productisation).

Lightweight, model-free: tariff plans are static; the tenant's current plan is
stored in tenant.settings["plan"]; usage is computed live from existing tables.
SLA endpoint reports DB + background-worker health.

GET  /billing/plans            — available tariff plans
GET  /billing/usage            — current tenant usage vs plan limits
POST /tenants/{id}/plan        — set a tenant's plan (super-admin)  [see tenants.py? kept here]
GET  /billing/sla              — service health snapshot
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import ActiveUser, get_db, require_permission
from app.models.auth import User
from app.models.inventory import Product
from app.models.ledger import LedgerEntry
from app.models.tenant import Tenant
from app.models.warehouse import Warehouse

router = APIRouter(tags=["billing"])
DB = Annotated[AsyncSession, Depends(get_db)]

# Static tariff catalogue. -1 = unlimited.
PLANS: dict[str, dict] = {
    "free":     {"label": "Free",     "max_warehouses": 1,  "max_users": 5,   "max_skus": 100,   "max_ledger_month": 5_000},
    "standard": {"label": "Standard", "max_warehouses": 3,  "max_users": 50,  "max_skus": 2_000, "max_ledger_month": 100_000},
    "pro":      {"label": "Pro",      "max_warehouses": -1, "max_users": -1,  "max_skus": -1,    "max_ledger_month": -1},
}


class PlanBody(BaseModel):
    plan: str


@router.get("/billing/plans")
async def list_plans() -> dict:
    return PLANS


@router.get("/billing/usage", dependencies=[require_permission("billing", "view")])
async def usage(user: ActiveUser, db: DB) -> dict:
    if user.tenant_id is None:
        raise HTTPException(status_code=400, detail="Tenant context required")
    tenant = await db.get(Tenant, user.tenant_id)
    plan_key = (tenant.settings or {}).get("plan", "standard") if tenant else "standard"
    plan = PLANS.get(plan_key, PLANS["standard"])

    wh = (await db.execute(
        select(func.count(Warehouse.id)).where(Warehouse.tenant_id == user.tenant_id)
    )).scalar_one()
    users = (await db.execute(
        select(func.count(User.id)).where(User.tenant_id == user.tenant_id)
    )).scalar_one()
    skus = (await db.execute(
        select(func.count(Product.id)).where(Product.tenant_id == user.tenant_id)
    )).scalar_one()
    now = datetime.now(timezone.utc)
    month_start = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
    ledger_month = (await db.execute(
        select(func.count(LedgerEntry.id)).where(
            LedgerEntry.tenant_id == user.tenant_id, LedgerEntry.created_at >= month_start
        )
    )).scalar_one()

    def over(used: int, limit: int) -> bool:
        return limit >= 0 and used > limit

    usage_map = {
        "warehouses": {"used": wh, "limit": plan["max_warehouses"], "over": over(wh, plan["max_warehouses"])},
        "users": {"used": users, "limit": plan["max_users"], "over": over(users, plan["max_users"])},
        "skus": {"used": skus, "limit": plan["max_skus"], "over": over(skus, plan["max_skus"])},
        "ledger_month": {"used": ledger_month, "limit": plan["max_ledger_month"], "over": over(ledger_month, plan["max_ledger_month"])},
    }
    return {
        "plan": plan_key,
        "plan_label": plan["label"],
        "usage": usage_map,
        "any_over_limit": any(v["over"] for v in usage_map.values()),
    }


@router.post("/tenants/{tenant_id}/plan", dependencies=[require_permission("billing", "update")])
async def set_plan(tenant_id: uuid.UUID, body: PlanBody, user: ActiveUser, db: DB) -> dict:
    if not user.is_superadmin:
        raise HTTPException(status_code=403, detail="Super-admin only")
    if body.plan not in PLANS:
        raise HTTPException(status_code=422, detail=f"Unknown plan: {body.plan}")
    tenant = await db.get(Tenant, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    tenant.settings = {**(tenant.settings or {}), "plan": body.plan}
    await db.commit()
    return {"tenant_id": str(tenant_id), "plan": body.plan}


@router.get("/billing/sla")
async def sla(db: DB) -> dict:
    """Service health snapshot (DB reachability + timestamp)."""
    db_ok = True
    try:
        await db.execute(select(func.now()))
    except Exception:
        db_ok = False
    return {
        "status": "ok" if db_ok else "degraded",
        "db": db_ok,
        "time": datetime.now(timezone.utc).isoformat(),
    }
