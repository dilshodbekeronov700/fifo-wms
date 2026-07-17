"""FastAPI dependency injections: current user, tenant context, RBAC."""
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import decode_token
from app.db.base import get_db
from app.models.auth import Role, User

bearer_scheme = HTTPBearer()


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(credentials.credentials)
    except JWTError:
        raise exc

    if payload.get("type") != "access":
        raise exc

    user_id: str | None = payload.get("sub")
    if user_id is None:
        raise exc

    result = await db.execute(
        select(User)
        .options(selectinload(User.roles).selectinload(Role.permissions))
        .where(User.id == UUID(user_id), User.is_active.is_(True))
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise exc
    return user


ActiveUser = Annotated[User, Depends(get_current_user)]


def require_permission(resource: str, action: str):
    """Returns a dependency that enforces RBAC; superadmin always passes."""

    async def _check(user: ActiveUser) -> User:
        if user.is_superadmin:
            return user
        # Flatten permissions from all roles
        allowed = {
            (p.resource, p.action)
            for role in user.roles
            for p in role.permissions
        }
        if (resource, action) not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {resource}:{action}",
            )
        return user

    return Depends(_check)


async def ensure_warehouse_access(db: AsyncSession, user: User, warehouse_id):
    """Verify the warehouse belongs to the user's tenant and is within the user's
    data scope (TZ §13.1 — tenant/scope isolation). Returns the Warehouse."""
    from app.models.warehouse import Warehouse  # local import avoids cycle

    wh = await db.get(Warehouse, warehouse_id)
    if wh is None or (not user.is_superadmin and wh.tenant_id != user.tenant_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Warehouse not found")
    scope = user.warehouse_scope or []
    if scope and not user.is_superadmin and str(warehouse_id) not in scope:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Warehouse out of your scope"
        )
    return wh
