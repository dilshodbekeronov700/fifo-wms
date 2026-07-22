"""WMS hujjatlari ro'yxati (kirim/chiqim/ko'chirish/...).

GET /documents/?warehouse_id=&doc_type=  — sklad + turi bo'yicha hujjatlar.
Kirim sahifasi (Приёмка) doc_type='receipt' bilan chaqiradi.
"""
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import ActiveUser, get_db
from app.models.inventory import Document, DocumentType

router = APIRouter(prefix="/documents", tags=["documents"])
DB = Annotated[AsyncSession, Depends(get_db)]


@router.get("/")
async def list_documents(
    user: ActiveUser,
    db: DB,
    warehouse_id: uuid.UUID | None = Query(None),
    doc_type: str | None = Query(None),
):
    """WMS Document qatorlari — tenant izolyatsiyasi majburiy; sklad + tur ixtiyoriy."""
    q = select(Document).where(Document.tenant_id == user.tenant_id)
    if warehouse_id is not None:
        q = q.where(Document.warehouse_id == warehouse_id)
    if doc_type:
        try:
            q = q.where(Document.doc_type == DocumentType(doc_type))
        except ValueError:
            return []
    q = q.order_by(Document.created_at.desc()).limit(500)
    rows = (await db.execute(q)).scalars().all()
    return [
        {
            "id": str(d.id),
            "doc_type": d.doc_type.value if hasattr(d.doc_type, "value") else d.doc_type,
            "status": d.status.value if hasattr(d.status, "value") else d.status,
            "external_id": d.external_id,
            "smartup_id": d.smartup_id,
            "notes": d.notes,
            "created_at": d.created_at,
            "updated_at": d.updated_at,
        }
        for d in rows
    ]
