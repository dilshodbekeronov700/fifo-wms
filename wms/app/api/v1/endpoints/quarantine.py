"""
Quarantine / QC module (TZ §12 — configurable).

Batches received under quarantine are blocked from picking until QC releases
them. Toggle per tenant via settings.quarantine_on_receipt.

GET   /quarantine/batches        — batches in quarantine/blocked
POST  /quarantine/{batch_id}/release  — quarantine → available
POST  /quarantine/{batch_id}/block    — available → blocked/quarantine
"""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import ActiveUser, get_db, require_permission
from app.models.inventory import Batch, BatchStatus, Product
from app.services import audit as audit_svc

router = APIRouter(prefix="/quarantine", tags=["quarantine"])
DB = Annotated[AsyncSession, Depends(get_db)]


class ReasonBody(BaseModel):
    reason: str | None = None


def _pname(p: Product) -> str | None:
    n = p.name
    if isinstance(n, dict):
        return n.get("uz") or n.get("ru") or n.get("en")
    return n or None


@router.get("/batches", dependencies=[require_permission("quarantine", "view")])
async def list_quarantine(user: ActiveUser, db: DB):
    rows = (await db.execute(
        select(Batch, Product).join(Product, Product.id == Batch.product_id).where(
            Product.tenant_id == user.tenant_id,
            Batch.status.in_([BatchStatus.QUARANTINE, BatchStatus.BLOCKED]),
        )
    )).all()
    return [
        {
            "id": str(b.id), "product_id": str(b.product_id),
            "product_name": _pname(p), "gtin": p.gtin,
            "lot_number": b.lot_number,
            "expiry_date": b.expiry_date, "status": b.status.value,
        }
        for b, p in rows
    ]


async def _get_batch(db: AsyncSession, user, batch_id: uuid.UUID) -> Batch:
    b = (await db.execute(
        select(Batch).join(Product, Product.id == Batch.product_id).where(
            Batch.id == batch_id, Product.tenant_id == user.tenant_id
        )
    )).scalar_one_or_none()
    if b is None:
        raise HTTPException(status_code=404, detail="Batch not found")
    return b


@router.post("/{batch_id}/release", dependencies=[require_permission("quarantine", "approve")])
async def release_batch(batch_id: uuid.UUID, body: ReasonBody, user: ActiveUser, db: DB):
    b = await _get_batch(db, user, batch_id)
    b.status = BatchStatus.AVAILABLE
    await audit_svc.record(
        db, action="quarantine_release", resource="batch", tenant_id=user.tenant_id,
        user_id=user.id, resource_id=str(batch_id), detail={"reason": body.reason},
    )
    await db.commit()
    return {"id": str(b.id), "status": b.status.value}


@router.post("/{batch_id}/block", dependencies=[require_permission("quarantine", "approve")])
async def block_batch(batch_id: uuid.UUID, body: ReasonBody, user: ActiveUser, db: DB):
    b = await _get_batch(db, user, batch_id)
    b.status = BatchStatus.BLOCKED
    await audit_svc.record(
        db, action="quarantine_block", resource="batch", tenant_id=user.tenant_id,
        user_id=user.id, resource_id=str(batch_id), detail={"reason": body.reason},
    )
    await db.commit()
    return {"id": str(b.id), "status": b.status.value}
