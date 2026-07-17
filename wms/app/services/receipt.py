"""
Receipt (kirim) service.

Flow (TZ §7.2):
  1. TSD sends transport codes (SSCC / BOX_LV).
  2. For each code: resolve via Asl Belgisi (owner-check + private/codes) — shared
     resolver in app.services.putaway.
  3. Persist the transport MarkingCode, write a RECEIPT ledger entry (qty = units,
     destination location still NULL — putaway sets it), and create a putaway Task.
  4. Finalise the document.

Code resolution lives in putaway.resolve_scanned_code so receipt and the live
putaway scan share one implementation.
"""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors.aslbelgisi import AslBelgisiClient
from app.models.inventory import (
    BatchStatus, Document, DocumentStatus, DocumentType,
    MarkingCode, MarkingCodeStatus, PackageType,
)
from app.models.exception import ExceptionType
from app.models.ledger import LedgerAction
from app.models.task import Task, TaskStatus, TaskType
from app.models.tenant import Tenant
from app.models.warehouse import Warehouse
from app.schemas.inventory import ReceiptCodeItem, ReceiptCodeResult, ReceiptOut
from app.services import exceptions as exc_svc
from app.services import ledger as ledger_svc
from app.services import putaway as putaway_svc


async def process_receipt(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    warehouse_id: uuid.UUID,
    user_id: uuid.UUID,
    codes: list[ReceiptCodeItem],
    notes: str | None,
    aslbelgisi_client: AslBelgisiClient,
    tenant_tin: str,
) -> ReceiptOut:
    # 1. Warehouse belongs to tenant
    wh = await db.execute(
        select(Warehouse).where(Warehouse.id == warehouse_id, Warehouse.tenant_id == tenant_id)
    )
    if wh.scalar_one_or_none() is None:
        raise ValueError("Warehouse not found for this tenant")

    # 2. Document header
    doc = Document(
        tenant_id=tenant_id,
        warehouse_id=warehouse_id,
        doc_type=DocumentType.RECEIPT,
        status=DocumentStatus.IN_PROGRESS,
        created_by=user_id,
        notes=notes,
    )
    db.add(doc)
    await db.flush()

    # Quarantine-on-receipt is a per-tenant toggle (configurable QC module).
    tenant = await db.get(Tenant, tenant_id)
    quarantine = bool((tenant.settings or {}).get("quarantine_on_receipt")) if tenant else False

    results: list[ReceiptCodeResult] = []

    for item in codes:
        resolved = await putaway_svc.resolve_scanned_code(
            db, tenant_id=tenant_id, code=item.code, client=aslbelgisi_client, tin=tenant_tin
        )

        if not resolved.ownership_ok:
            # Escalate as an exception (TZ §7.13)
            etype = (
                ExceptionType.FORBIDDEN_OWNER if resolved.reason == "forbidden_owner"
                else ExceptionType.UNKNOWN_CODE
            )
            await exc_svc.record(
                db, tenant_id=tenant_id, warehouse_id=warehouse_id, exc_type=etype,
                marking_code=item.code, created_by=user_id, severity=70,
                message=f"Receipt scan rejected: {resolved.reason}",
                detail={"document_id": str(doc.id)},
            )
            results.append(ReceiptCodeResult(
                code=item.code, package_type=item.package_type, gtin=None,
                nested_count=0, product_id=None, batch_id=None,
                ownership_ok=False, error=resolved.reason or "ownership_failed",
            ))
            continue

        # Quarantine the batch on receipt if configured
        if quarantine and resolved.batch and resolved.batch.status != BatchStatus.QUARANTINE:
            resolved.batch.status = BatchStatus.QUARANTINE

        # Persist the scanned transport code
        await _upsert_marking_code(
            db,
            tenant_id=tenant_id,
            code=item.code,
            gtin=resolved.gtin,
            package_type=resolved.package_type or item.package_type.value,
            product_id=resolved.product.id if resolved.product else None,
            batch_id=resolved.batch.id if resolved.batch else None,
        )

        # Persist the immediate children (box level) with parent link — recall
        # traceability (TZ §12: every KIZ → batch → which dock/customer).
        for child in resolved.children:
            await _upsert_marking_code(
                db,
                tenant_id=tenant_id,
                code=child,
                gtin=resolved.gtin,
                package_type="GROUP",
                product_id=resolved.product.id if resolved.product else None,
                batch_id=resolved.batch.id if resolved.batch else None,
                parent_code=item.code,
            )

        # SKU not mapped → escalate (still received, but needs master-data fix)
        if resolved.product is None:
            await exc_svc.record(
                db, tenant_id=tenant_id, warehouse_id=warehouse_id,
                exc_type=ExceptionType.PRODUCT_NOT_MAPPED, marking_code=item.code,
                created_by=user_id, severity=40,
                message=f"GTIN {resolved.gtin} not mapped to a product",
            )

        # RECEIPT ledger entry (location set later by putaway)
        if resolved.product and resolved.unit_count > 0:
            await ledger_svc.record(
                db,
                tenant_id=tenant_id,
                warehouse_id=warehouse_id,
                action=LedgerAction.RECEIPT,
                qty_delta=resolved.unit_count,
                product_id=resolved.product.id,
                batch_id=resolved.batch.id if resolved.batch else None,
                marking_code=item.code,
                to_location_id=None,
                user_id=user_id,
                document_id=doc.id,
                reason="receipt_scan",
                extra={
                    "transport_code": item.code,
                    "box_count": resolved.box_count,
                    "counting_method": resolved.counting_method,
                },
            )

            # Putaway task for the operator
            db.add(Task(
                tenant_id=tenant_id,
                warehouse_id=warehouse_id,
                task_type=TaskType.PUTAWAY,
                status=TaskStatus.PENDING,
                document_id=doc.id,
                payload={
                    "product_id": str(resolved.product.id),
                    "batch_id": str(resolved.batch.id) if resolved.batch else None,
                    "marking_code": item.code,
                    "qty": resolved.unit_count,
                    "box_count": resolved.box_count,
                    "source": "receipt",
                },
            ))

        results.append(ReceiptCodeResult(
            code=item.code,
            package_type=item.package_type,
            gtin=resolved.gtin,
            nested_count=resolved.box_count or len(resolved.children),
            product_id=resolved.product.id if resolved.product else None,
            batch_id=resolved.batch.id if resolved.batch else None,
            ownership_ok=True,
            error=None if resolved.product else "product_not_mapped",
        ))

    all_ok = all(r.ownership_ok and r.error is None for r in results)
    doc.status = DocumentStatus.COMPLETED if all_ok else DocumentStatus.IN_PROGRESS
    await db.commit()

    return ReceiptOut(document_id=doc.id, status=doc.status.value, results=results)


async def _upsert_marking_code(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    code: str,
    gtin: str | None,
    package_type: str,
    product_id: uuid.UUID | None,
    batch_id: uuid.UUID | None,
    parent_code: str | None = None,
) -> None:
    result = await db.execute(select(MarkingCode).where(MarkingCode.code == code))
    mc = result.scalar_one_or_none()
    try:
        pkg = PackageType(package_type)
    except ValueError:
        pkg = PackageType.BOX_LV_1
    if mc is None:
        db.add(MarkingCode(
            tenant_id=tenant_id,
            code=code,
            gtin=gtin,
            package_type=pkg,
            parent_code=parent_code,
            mc_status=MarkingCodeStatus.RECEIVED,
            product_id=product_id,
            batch_id=batch_id,
        ))
    else:
        if product_id and mc.product_id is None:
            mc.product_id = product_id
        if batch_id and mc.batch_id is None:
            mc.batch_id = batch_id
        if parent_code and mc.parent_code is None:
            mc.parent_code = parent_code
