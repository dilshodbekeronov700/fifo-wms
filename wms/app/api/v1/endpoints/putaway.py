"""
Putaway endpoints (TSD) — directed slotting with a reserve → confirm-by-scan flow.

  POST /putaway/scan-suggest      Scan a transport/pallet code → resolved detail +
                                  ranked slot candidates (with per-factor breakdown).
  GET  /putaway/locations/search  Manual slot lookup (operator override).
  POST /putaway/reserve           Hold a slot for the scanned code (bron). No stock move.
  POST /putaway/confirm           Operator scanned the slot QR/DataMatrix → place stock.
  POST /putaway/cancel            Release a held reservation.
  GET  /putaway/reservations      List pending reservations (manager / map overlay).

The two-step reserve/confirm flow is deliberate: a suggestion is a *booking*, not
a placement. Stock only moves once the operator physically scans the location
barcode — which both proves the goods reached the slot and prevents two operators
racing for the same location.
"""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.connector_factory import get_aslbelgisi_client, get_tenant_tin
from app.core.deps import ActiveUser, get_db, require_permission
from app.models.reservation import PutawayReservation, ReservationStatus
from app.models.warehouse import Warehouse
from app.schemas.inventory import (
    CancelRequest,
    ConfirmRequest,
    LocationOptionOut,
    PalletScanRequest,
    PutawaySuggestionOut,
    ReservationOut,
    ReserveRequest,
    ResolvedCodeOut,
    SlotCandidateOut,
)
from app.services import putaway as putaway_svc

router = APIRouter(prefix="/putaway", tags=["putaway"])
DB = Annotated[AsyncSession, Depends(get_db)]

_ERROR_STATUS = {
    "location_not_found": 404,
    "product_not_found": 404,
    "reservation_not_found": 404,
}


async def _check_warehouse(db: AsyncSession, user: ActiveUser, warehouse_id: uuid.UUID) -> Warehouse:
    if user.tenant_id is None:
        raise HTTPException(status_code=400, detail="Tenant context required")
    wh = await db.get(Warehouse, warehouse_id)
    if wh is None or wh.tenant_id != user.tenant_id:
        raise HTTPException(status_code=404, detail="Warehouse not found")
    return wh


def _http(err: putaway_svc.PutawayError) -> HTTPException:
    code = str(err)
    return HTTPException(status_code=_ERROR_STATUS.get(code, 409), detail=code)


def _candidate_out(c: putaway_svc.SlotCandidate) -> SlotCandidateOut:
    return SlotCandidateOut(
        location_id=c.location_id, location_code=c.location_code,
        zone_id=c.zone_id, zone_type=c.zone_type, score=c.score,
        reason=c.reason, factors=c.factors, remaining_boxes=c.remaining_boxes,
    )


@router.post(
    "/scan-suggest",
    response_model=PutawaySuggestionOut,
    dependencies=[require_permission("putaway", "create")],
)
async def scan_suggest(body: PalletScanRequest, user: ActiveUser, db: DB):
    await _check_warehouse(db, user, body.warehouse_id)

    client = await get_aslbelgisi_client(db, user.tenant_id)
    tin = await get_tenant_tin(db, user.tenant_id)

    sug = await putaway_svc.scan_and_suggest(
        db, tenant_id=user.tenant_id, warehouse_id=body.warehouse_id,
        code=body.code, client=client, tin=tin, top_n=body.top_n,
    )
    await db.commit()  # persist any batch created during resolution

    r = sug.resolved
    resolved_out = ResolvedCodeOut(
        code=r.code, ownership_ok=r.ownership_ok, reason=r.reason,
        package_type=r.package_type, product_group_id=r.product_group_id,
        issuer_tin=r.issuer_tin, gtin=r.gtin, expiry_date=r.expiry_date,
        production_date=r.production_date, box_count=r.box_count,
        unit_count=r.unit_count, counting_method=r.counting_method,
        product_id=r.product.id if r.product else None,
        product_name=r.product.name if r.product else None,
        batch_id=r.batch.id if r.batch else None,
        children=r.children,
    )
    candidates = [_candidate_out(c) for c in sug.candidates]
    return PutawaySuggestionOut(
        resolved=resolved_out,
        suggested=candidates[0] if candidates else None,
        candidates=candidates,
    )


@router.get(
    "/locations/search",
    response_model=list[LocationOptionOut],
    dependencies=[require_permission("putaway", "create")],
)
async def locations_search(
    user: ActiveUser,
    db: DB,
    warehouse_id: uuid.UUID,
    q: str | None = Query(default=None),
    product_id: uuid.UUID | None = Query(default=None),
    batch_id: uuid.UUID | None = Query(default=None),
    qty: int = Query(default=1, ge=1),
    limit: int = Query(default=25, ge=1, le=100),
):
    await _check_warehouse(db, user, warehouse_id)
    opts = await putaway_svc.search_locations(
        db, warehouse_id=warehouse_id, product_id=product_id,
        batch_id=batch_id, qty=qty, query=q, limit=limit,
    )
    await db.commit()
    return [LocationOptionOut(**o.__dict__) for o in opts]


@router.post(
    "/reserve",
    response_model=ReservationOut,
    dependencies=[require_permission("putaway", "create")],
)
async def reserve(body: ReserveRequest, user: ActiveUser, db: DB):
    await _check_warehouse(db, user, body.warehouse_id)
    try:
        res = await putaway_svc.reserve_slot(
            db, tenant_id=user.tenant_id, warehouse_id=body.warehouse_id,
            code=body.code, location_id=body.location_id, product_id=body.product_id,
            batch_id=body.batch_id, qty=body.qty, unit_count=body.unit_count,
            package_type=body.package_type, score=body.score, reason=body.reason,
            manual=body.manual, force=body.force, payload=body.payload, user_id=user.id,
        )
    except putaway_svc.PutawayError as e:
        await db.rollback()
        raise _http(e)
    await db.commit()
    return ReservationOut.model_validate(res)


@router.post(
    "/confirm",
    dependencies=[require_permission("putaway", "create")],
)
async def confirm(body: ConfirmRequest, user: ActiveUser, db: DB):
    """Joylashni tasdiqlaydi — IKKI APK formatini ham qo'llab-quvvatlaydi.

    • Yangi oqim: reservation_id + location_barcode  → reservation-based confirm.
    • Eski oqim: task_id + location_id               → task-based confirm (eski APK).
    """
    if user.tenant_id is None:
        raise HTTPException(status_code=400, detail="Tenant context required")

    # ── Yangi (reservation-based) oqim ───────────────────────────────────────
    if body.reservation_id is not None and body.location_barcode:
        try:
            res = await putaway_svc.confirm_putaway(
                db, tenant_id=user.tenant_id, reservation_id=body.reservation_id,
                scanned_location=body.location_barcode, user_id=user.id,
            )
        except putaway_svc.PutawayError as e:
            await db.rollback()
            raise _http(e)
        await db.commit()
        out = ReservationOut.model_validate(res).model_dump(mode="json")
        placed_code, loc_id = res.code, res.location_id

        # Yacheykaga qo'yilgan zahoti — Asl Belgisi shajara daraxti + 9.2 to'liq
        # ma'lumot (GTIN/muddat/partiya) ni AVTOMATIK tortadi. best-effort:
        # kod (transport/box/group/unit) farqi yo'q — build_code_tree TEPAGA root
        # topib PASTGA yig'adi. Kvota/xato TSD tasdig'ini TO'XTATMAYDI.
        try:
            from app.core.connector_factory import get_aslbelgisi_client
            from app.services.marking_tree import build_code_tree
            client = await get_aslbelgisi_client(db, user.tenant_id)
            enrich = await build_code_tree(
                db, tenant_id=user.tenant_id, root_code=placed_code,
                location_id=loc_id, aslbelgisi_client=client,
            )
            out["code_tree"] = enrich
        except Exception as exc:
            out["code_tree_error"] = f"{type(exc).__name__}: {exc}"
        return out

    # ── Eski (task-based) oqim — backward-compat (eski APK hali ishlasin) ────
    if body.task_id is not None and body.location_id is not None:
        from app.api.v1.endpoints.receipt import putaway_confirm as _task_confirm
        from app.schemas.inventory import PutawayConfirm
        return await _task_confirm(
            PutawayConfirm(task_id=body.task_id, location_id=body.location_id),
            user, db,
        )

    raise HTTPException(
        status_code=422,
        detail="reservation_id+location_barcode yoki task_id+location_id kerak",
    )


@router.post(
    "/cancel",
    response_model=ReservationOut,
    dependencies=[require_permission("putaway", "create")],
)
async def cancel(body: CancelRequest, user: ActiveUser, db: DB):
    if user.tenant_id is None:
        raise HTTPException(status_code=400, detail="Tenant context required")
    try:
        res = await putaway_svc.cancel_reservation(
            db, tenant_id=user.tenant_id, reservation_id=body.reservation_id,
        )
    except putaway_svc.PutawayError as e:
        await db.rollback()
        raise _http(e)
    await db.commit()
    return ReservationOut.model_validate(res)


@router.get(
    "/reservations",
    response_model=list[ReservationOut],
    dependencies=[require_permission("putaway", "view")],
)
async def list_reservations(
    user: ActiveUser,
    db: DB,
    warehouse_id: uuid.UUID,
    status: ReservationStatus = Query(default=ReservationStatus.PENDING),
):
    await _check_warehouse(db, user, warehouse_id)
    await putaway_svc.expire_stale_reservations(db, warehouse_id=warehouse_id)
    rows = (await db.execute(
        select(PutawayReservation)
        .where(
            PutawayReservation.warehouse_id == warehouse_id,
            PutawayReservation.status == status,
        )
        .order_by(PutawayReservation.created_at.desc())
        .limit(200)
    )).scalars().all()
    await db.commit()
    return [ReservationOut.model_validate(r) for r in rows]
