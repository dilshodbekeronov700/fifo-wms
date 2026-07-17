"""Platform administration — RBAC seeding (super-admin only)."""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import ActiveUser, get_db
from app.core.seed import seed_rbac

router = APIRouter(prefix="/admin", tags=["admin"])
DB = Annotated[AsyncSession, Depends(get_db)]


@router.post("/seed-rbac")
async def seed_rbac_endpoint(user: ActiveUser, db: DB) -> dict:
    """Upsert the permission catalog and built-in system roles.

    Idempotent — safe to call repeatedly. Super-admin only.
    """
    if not user.is_superadmin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Super-admin only"
        )
    counts = await seed_rbac(db)
    await db.commit()
    return counts
