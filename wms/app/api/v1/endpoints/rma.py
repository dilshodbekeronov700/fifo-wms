"""RMA endpoint — mijoz qaytarishi + tasnif (restock/quarantine/scrap)."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import ActiveUser, ensure_warehouse_access, get_db, require_permission
from app.schemas.planning import RmaCreateIn, RmaOut
from app.services import rma as rma_svc

router = APIRouter(prefix="/rma", tags=["rma"])
DB = Annotated[AsyncSession, Depends(get_db)]


@router.post("", response_model=RmaOut, status_code=201,
             dependencies=[require_permission("return", "create")])
async def create_rma(body: RmaCreateIn, user: ActiveUser, db: DB):
    if user.tenant_id is None:
        raise HTTPException(status_code=400, detail="Tenant context required")
    await ensure_warehouse_access(db, user, body.warehouse_id)
    try:
        lines = [rma_svc.RmaLine(
            product_id=ln.product_id, batch_id=ln.batch_id, qty=ln.qty,
            disposition=rma_svc.Disposition(ln.disposition),
            location_id=ln.location_id, marking_codes=ln.marking_codes)
            for ln in body.lines]
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid disposition (restock|quarantine|scrap)")
    try:
        res = await rma_svc.process_rma(
            db, tenant_id=user.tenant_id, warehouse_id=body.warehouse_id,
            lines=lines, user_id=user.id, external_id=body.external_id, notes=body.notes)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    await db.commit()
    return RmaOut(document_id=res.document_id, restocked=res.restocked,
                  quarantined=res.quarantined, scrapped=res.scrapped)
