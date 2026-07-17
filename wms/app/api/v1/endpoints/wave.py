"""Wave picking endpoint — bir nechta buyurtmani marshrutlangan terish ro'yxati."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import ActiveUser, ensure_warehouse_access, get_db, require_permission
from app.schemas.planning import (
    WaveInstructionOut, WavePlanIn, WavePlanOut, WaveStopOut,
)
from app.services import wave as wave_svc

router = APIRouter(prefix="/wave", tags=["wave"])
DB = Annotated[AsyncSession, Depends(get_db)]


@router.post("/plan", response_model=WavePlanOut,
             dependencies=[require_permission("shipment", "view")])
async def wave_plan(body: WavePlanIn, user: ActiveUser, db: DB):
    if not body.lines:
        raise HTTPException(status_code=422, detail="At least one line required")
    await ensure_warehouse_access(db, user, body.warehouse_id)
    plan = await wave_svc.build_wave_plan(
        db, warehouse_id=body.warehouse_id,
        lines=[wave_svc.WaveLineRequest(
            order_line_id=ln.order_line_id, product_id=ln.product_id,
            requested_boxes=ln.requested_boxes, order_id=ln.order_id)
            for ln in body.lines],
    )
    return WavePlanOut(
        warehouse_id=plan.warehouse_id,
        stops=[WaveStopOut(
            sequence=st.sequence, location_id=st.location_id, location_code=st.location_code,
            instructions=[WaveInstructionOut(**i.__dict__) for i in st.instructions])
            for st in plan.stops],
        shortfalls=plan.shortfalls, total_lines=plan.total_lines, total_boxes=plan.total_boxes,
    )
