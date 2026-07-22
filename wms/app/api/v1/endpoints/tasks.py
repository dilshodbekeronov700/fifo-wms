"""Operator vazifalari — ro'yxat + holatni yangilash.

GET   /tasks/          — sklad/holat/turi bo'yicha vazifalar (Dashboard KPI
                         'ochiq vazifalar' bilan bir xil manba: tasks jadvali)
PATCH /tasks/{id}      — vazifa holatini o'zgartirish (Boshlash/Tugallash/Bekor)
"""
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import ActiveUser, get_db
from app.models.task import Task, TaskStatus, TaskType

router = APIRouter(prefix="/tasks", tags=["tasks"])
DB = Annotated[AsyncSession, Depends(get_db)]


def _task_out(t: Task) -> dict:
    return {
        "id": str(t.id),
        "task_type": t.task_type.value if hasattr(t.task_type, "value") else t.task_type,
        "status": t.status.value if hasattr(t.status, "value") else t.status,
        "priority": t.priority,
        "payload": t.payload or {},
        "document_id": str(t.document_id) if t.document_id else None,
        "assigned_to": str(t.assigned_to) if t.assigned_to else None,
        "created_at": t.created_at,
        "updated_at": t.updated_at,
    }


@router.get("/")
async def list_tasks(
    user: ActiveUser,
    db: DB,
    warehouse_id: uuid.UUID | None = Query(None),
    status: str | None = Query(None),
    task_type: str | None = Query(None),
):
    """Operator vazifalari. Tenant izolyatsiyasi majburiy; sklad/holat/tur — ixtiyoriy filtr."""
    q = select(Task).where(Task.tenant_id == user.tenant_id)
    if warehouse_id is not None:
        q = q.where(Task.warehouse_id == warehouse_id)
    if status:
        try:
            q = q.where(Task.status == TaskStatus(status))
        except ValueError:
            raise HTTPException(status_code=422, detail=f"Noto'g'ri holat: {status}")
    if task_type:
        try:
            q = q.where(Task.task_type == TaskType(task_type))
        except ValueError:
            raise HTTPException(status_code=422, detail=f"Noto'g'ri tur: {task_type}")
    q = q.order_by(Task.priority.desc(), Task.created_at.desc()).limit(500)
    rows = (await db.execute(q)).scalars().all()
    return [_task_out(t) for t in rows]


class TaskPatch(BaseModel):
    status: str | None = None
    priority: int | None = None
    assigned_to: uuid.UUID | None = None


@router.patch("/{task_id}")
async def update_task(task_id: uuid.UUID, body: TaskPatch, user: ActiveUser, db: DB):
    t = (await db.execute(
        select(Task).where(Task.id == task_id, Task.tenant_id == user.tenant_id)
    )).scalar_one_or_none()
    if t is None:
        raise HTTPException(status_code=404, detail="Task not found")
    if body.status is not None:
        try:
            t.status = TaskStatus(body.status)
        except ValueError:
            raise HTTPException(status_code=422, detail=f"Noto'g'ri holat: {body.status}")
    if body.priority is not None:
        t.priority = body.priority
    if body.assigned_to is not None:
        t.assigned_to = body.assigned_to
    await db.commit()
    await db.refresh(t)
    return _task_out(t)
