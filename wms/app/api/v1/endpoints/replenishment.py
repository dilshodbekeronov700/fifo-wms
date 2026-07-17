"""Replenishment endpoints — reserve→pick to'ldirish (safety-stock asosida)."""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import ActiveUser, ensure_warehouse_access, get_db, require_permission
from app.schemas.planning import (
    ReplenishExecuteIn, ReplenishGenerateOut, ReplenishItem, ReplenishPlanOut,
)
from app.services import replenishment as rep

router = APIRouter(prefix="/replenishment", tags=["replenishment"])
DB = Annotated[AsyncSession, Depends(get_db)]


@router.get("/plan", response_model=ReplenishPlanOut,
            dependencies=[require_permission("movement", "view")])
async def replenishment_plan(warehouse_id: uuid.UUID, user: ActiveUser, db: DB, threshold: int = 0):
    await ensure_warehouse_access(db, user, warehouse_id)
    sugg = await rep.compute_replenishments(db, warehouse_id=warehouse_id, threshold=threshold)
    return ReplenishPlanOut(
        warehouse_id=warehouse_id,
        suggestions=[ReplenishItem(**s.__dict__) for s in sugg],
    )


@router.post("/tasks", response_model=ReplenishGenerateOut, status_code=201,
             dependencies=[require_permission("movement", "create")])
async def generate_replenishment_tasks(
    warehouse_id: uuid.UUID, user: ActiveUser, db: DB, threshold: int = 0,
):
    if user.tenant_id is None:
        raise HTTPException(status_code=400, detail="Tenant context required")
    await ensure_warehouse_access(db, user, warehouse_id)
    sugg = await rep.compute_replenishments(db, warehouse_id=warehouse_id, threshold=threshold)
    tasks = await rep.generate_tasks(
        db, tenant_id=user.tenant_id, warehouse_id=warehouse_id, suggestions=sugg)
    await db.commit()
    return ReplenishGenerateOut(created=len(tasks), task_ids=[t.id for t in tasks])


@router.post("/execute", status_code=200,
             dependencies=[require_permission("movement", "create")])
async def execute_replenishment(body: ReplenishExecuteIn, user: ActiveUser, db: DB):
    if user.tenant_id is None:
        raise HTTPException(status_code=400, detail="Tenant context required")
    await ensure_warehouse_access(db, user, body.warehouse_id)
    try:
        await rep.execute_move(
            db, tenant_id=user.tenant_id, warehouse_id=body.warehouse_id,
            product_id=body.product_id, batch_id=body.batch_id,
            from_location_id=body.from_location_id, to_location_id=body.to_location_id,
            qty=body.qty, user_id=user.id, task_id=body.task_id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    await db.commit()
    return {"status": "ok"}
