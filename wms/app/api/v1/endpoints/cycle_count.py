"""Cycle count endpoints — davriy inventarizatsiya tasklari + variance."""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import ActiveUser, ensure_warehouse_access, get_db, require_permission
from app.schemas.planning import (
    CycleGenerateIn, CycleGenerateOut, CycleRecordIn, CycleRecordOut,
    CycleTaskOut, CycleVarianceOut,
)
from app.services import cycle_count as cc

router = APIRouter(prefix="/cycle-count", tags=["cycle-count"])
DB = Annotated[AsyncSession, Depends(get_db)]


@router.post("/tasks", response_model=CycleGenerateOut, status_code=201,
             dependencies=[require_permission("inventory", "create")])
async def generate_cycle_tasks(body: CycleGenerateIn, user: ActiveUser, db: DB):
    if user.tenant_id is None:
        raise HTTPException(status_code=400, detail="Tenant context required")
    await ensure_warehouse_access(db, user, body.warehouse_id)
    tasks = await cc.generate_count_tasks(
        db, tenant_id=user.tenant_id, warehouse_id=body.warehouse_id, limit=body.limit)
    await db.commit()
    return CycleGenerateOut(
        created=len(tasks),
        tasks=[CycleTaskOut(task_id=t.id, location_id=uuid.UUID(t.payload["location_id"]),
                            location_code=t.payload["location_code"], priority=t.priority)
               for t in tasks],
    )


@router.post("/record", response_model=CycleRecordOut,
             dependencies=[require_permission("inventory", "create")])
async def record_cycle_count(body: CycleRecordIn, user: ActiveUser, db: DB):
    if user.tenant_id is None:
        raise HTTPException(status_code=400, detail="Tenant context required")
    await ensure_warehouse_access(db, user, body.warehouse_id)
    var = await cc.record_count(
        db, tenant_id=user.tenant_id, warehouse_id=body.warehouse_id,
        location_id=body.location_id,
        counted=[(ln.product_id, ln.batch_id, ln.counted_qty) for ln in body.lines],
        user_id=user.id, task_id=body.task_id)
    await db.commit()
    return CycleRecordOut(variances=[CycleVarianceOut(**v.__dict__) for v in var])


@router.get("/variance", dependencies=[require_permission("inventory", "view")])
async def cycle_variance(warehouse_id: uuid.UUID, user: ActiveUser, db: DB):
    await ensure_warehouse_access(db, user, warehouse_id)
    return await cc.variance_summary(db, warehouse_id=warehouse_id)
