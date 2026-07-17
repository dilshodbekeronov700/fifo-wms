"""
Label printing endpoints (TZ §7.12).

Generate Zebra ZPL strings for location and pallet (SSCC) labels. The ZPL is
returned as JSON so the frontend can either send it straight to a networked
Zebra printer or show a textual preview.

GET /labels/location/{location_id}  -> {"zpl": ..., "preview": ...}
GET /labels/pallet/{marking_code}   -> {"zpl": ..., "preview": ...}
"""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import ActiveUser, ensure_warehouse_access, get_db, require_permission
from app.models.inventory import MarkingCode, Product
from app.models.warehouse import Location, Warehouse, Zone
from app.services import labels as label_svc

router = APIRouter(prefix="/labels", tags=["labels"])
DB = Annotated[AsyncSession, Depends(get_db)]


def _product_name(name: dict | None) -> str:
    if not name:
        return ""
    if isinstance(name, dict):
        return name.get("ru") or name.get("uz") or next(iter(name.values()), "")
    return str(name)


@router.get("/location/{location_id}", dependencies=[require_permission("label", "view")])
async def get_location_label(location_id: uuid.UUID, user: ActiveUser, db: DB):
    if user.tenant_id is None:
        raise HTTPException(status_code=403, detail="No tenant")

    row = (await db.execute(
        select(Location, Zone, Warehouse)
        .join(Zone, Zone.id == Location.zone_id)
        .join(Warehouse, Warehouse.id == Zone.warehouse_id)
        .where(Location.id == location_id, Warehouse.tenant_id == user.tenant_id)
    )).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Location not found")

    loc, zone, warehouse = row
    await ensure_warehouse_access(db, user, warehouse.id)

    human = f"{zone.name} / {loc.code}" if zone.name else loc.code
    zpl = label_svc.location_label_zpl(code=loc.code, barcode=loc.barcode, human=human)
    preview = f"LOCATION {loc.code}  |  {human}  |  barcode={loc.barcode or loc.code}"
    return {"zpl": zpl, "preview": preview}


@router.get("/pallet/{marking_code}", dependencies=[require_permission("label", "view")])
async def get_pallet_label(marking_code: str, user: ActiveUser, db: DB):
    if user.tenant_id is None:
        raise HTTPException(status_code=403, detail="No tenant")

    mc = (await db.execute(
        select(MarkingCode).where(
            MarkingCode.code == marking_code,
            MarkingCode.tenant_id == user.tenant_id,
        )
    )).scalar_one_or_none()
    if mc is None:
        raise HTTPException(status_code=404, detail="Marking code not found")

    product_name = ""
    if mc.product_id is not None:
        product = (await db.execute(
            select(Product).where(
                Product.id == mc.product_id, Product.tenant_id == user.tenant_id
            )
        )).scalar_one_or_none()
        if product is not None:
            product_name = _product_name(product.name)

    batch_str = str(mc.batch_id) if mc.batch_id is not None else None
    zpl = label_svc.pallet_label_zpl(
        sscc=mc.code, product_name=product_name, qty=0, batch=batch_str
    )
    preview = f"PALLET {mc.code}  |  {product_name or '-'}  |  batch={batch_str or '-'}"
    return {"zpl": zpl, "preview": preview}
