"""
User / role / permission administration + audit-log viewer (P4).

  GET   /admin/users?status=pending|active|all   list users (tenant-scoped)
  POST  /admin/users/{id}/approve                 approve a sign-up + assign roles
  POST  /admin/users/{id}/reject                  reject a pending sign-up
  PATCH /admin/users/{id}                          activate/deactivate, set roles, scope
  GET   /admin/roles                               roles with their permissions
  POST  /admin/roles                               create a custom (tenant) role
  PUT   /admin/roles/{id}/permissions              set a role's permission set
  GET   /admin/permissions                         the full capability catalogue
  GET   /admin/audit                               immutable change log (filterable)

All endpoints are guarded by RBAC; super-admin bypasses. Tenant admins only see
and manage users/roles/audit within their own tenant.
"""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.deps import ActiveUser, get_db, require_permission
from app.models.audit import AuditLog
from app.models.auth import Permission, Role, User
from app.services import audit as audit_svc

router = APIRouter(prefix="/admin", tags=["admin"])
DB = Annotated[AsyncSession, Depends(get_db)]


# ─── Schemas ─────────────────────────────────────────────────────────────────

class UserOut(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    phone: str | None = None
    is_active: bool
    is_approved: bool
    is_superadmin: bool
    warehouse_scope: list = []
    roles: list[str] = []
    role_ids: list[uuid.UUID] = []
    created_at: str | None = None


class ApproveRequest(BaseModel):
    role_ids: list[uuid.UUID] = []


class UserPatch(BaseModel):
    is_active: bool | None = None
    full_name: str | None = None
    role_ids: list[uuid.UUID] | None = None
    warehouse_scope: list | None = None


class RoleOut(BaseModel):
    id: uuid.UUID
    name: str
    is_system: bool
    tenant_id: uuid.UUID | None = None
    permissions: list[str] = []          # "resource:action"
    permission_ids: list[uuid.UUID] = []
    user_count: int = 0


class RoleCreate(BaseModel):
    name: str


class RolePermissions(BaseModel):
    permission_ids: list[uuid.UUID]


class PermissionOut(BaseModel):
    id: uuid.UUID
    resource: str
    action: str
    description: str | None = None


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _tenant_filter(user: User):
    """Restrict to the caller's tenant (super-admin: no restriction)."""
    return None if user.is_superadmin else user.tenant_id


def _user_out(u: User) -> UserOut:
    return UserOut(
        id=u.id, email=u.email, full_name=u.full_name, phone=u.phone,
        is_active=u.is_active, is_approved=u.is_approved, is_superadmin=u.is_superadmin,
        warehouse_scope=u.warehouse_scope or [],
        roles=[r.name for r in u.roles], role_ids=[r.id for r in u.roles],
        created_at=u.created_at.isoformat() if u.created_at else None,
    )


async def _load_user(db: AsyncSession, user_id: uuid.UUID, caller: User) -> User:
    u = (await db.execute(
        select(User).where(User.id == user_id).options(selectinload(User.roles))
    )).scalar_one_or_none()
    if u is None:
        raise HTTPException(status_code=404, detail="user_not_found")
    if not caller.is_superadmin and u.tenant_id != caller.tenant_id:
        raise HTTPException(status_code=404, detail="user_not_found")
    return u


async def _resolve_roles(db: AsyncSession, role_ids: list[uuid.UUID], caller: User) -> list[Role]:
    if not role_ids:
        return []
    roles = (await db.execute(
        select(Role).where(Role.id.in_(role_ids))
    )).scalars().all()
    for r in roles:
        # tenant roles must belong to the caller's tenant; system roles are shared
        if r.tenant_id is not None and not caller.is_superadmin and r.tenant_id != caller.tenant_id:
            raise HTTPException(status_code=403, detail="role_out_of_scope")
    return list(roles)


# ─── Users ───────────────────────────────────────────────────────────────────

@router.get("/users", response_model=list[UserOut],
            dependencies=[require_permission("user", "view")])
async def list_users(
    user: ActiveUser, db: DB,
    status: str = Query(default="all", pattern="^(all|pending|active|inactive)$"),
):
    q = select(User).options(selectinload(User.roles))
    tid = _tenant_filter(user)
    if tid is not None:
        q = q.where(User.tenant_id == tid)
    if status == "pending":
        q = q.where(User.is_approved.is_(False), User.is_active.is_(True))
    elif status == "active":
        q = q.where(User.is_approved.is_(True), User.is_active.is_(True))
    elif status == "inactive":
        q = q.where(User.is_active.is_(False))
    rows = (await db.execute(q.order_by(User.created_at.desc()))).scalars().all()
    return [_user_out(u) for u in rows]


@router.post("/users/{user_id}/approve", response_model=UserOut,
             dependencies=[require_permission("user", "approve")])
async def approve_user(user_id: uuid.UUID, body: ApproveRequest,
                       user: ActiveUser, db: DB, request: Request):
    u = await _load_user(db, user_id, user)
    u.is_approved = True
    u.is_active = True
    if body.role_ids:
        u.roles = await _resolve_roles(db, body.role_ids, user)
    await audit_svc.record(
        db, action="user_approved", resource="user", tenant_id=u.tenant_id,
        user_id=user.id, resource_id=str(u.id),
        ip=request.client.host if request.client else None,
        detail={"by": user.email, "roles": [str(x) for x in body.role_ids]},
    )
    await db.commit()
    await db.refresh(u, ["roles"])
    return _user_out(u)


@router.post("/users/{user_id}/reject", response_model=UserOut,
             dependencies=[require_permission("user", "approve")])
async def reject_user(user_id: uuid.UUID, user: ActiveUser, db: DB, request: Request):
    u = await _load_user(db, user_id, user)
    u.is_active = False
    u.is_approved = False
    await audit_svc.record(
        db, action="user_rejected", resource="user", tenant_id=u.tenant_id,
        user_id=user.id, resource_id=str(u.id),
        ip=request.client.host if request.client else None, detail={"by": user.email},
    )
    await db.commit()
    await db.refresh(u, ["roles"])
    return _user_out(u)


@router.patch("/users/{user_id}", response_model=UserOut,
              dependencies=[require_permission("user", "update")])
async def update_user(user_id: uuid.UUID, body: UserPatch,
                      user: ActiveUser, db: DB, request: Request):
    u = await _load_user(db, user_id, user)
    changed = {}
    if body.is_active is not None:
        u.is_active = body.is_active
        changed["is_active"] = body.is_active
    if body.full_name is not None:
        u.full_name = body.full_name
        changed["full_name"] = body.full_name
    if body.warehouse_scope is not None:
        u.warehouse_scope = body.warehouse_scope
        changed["warehouse_scope"] = body.warehouse_scope
    if body.role_ids is not None:
        u.roles = await _resolve_roles(db, body.role_ids, user)
        changed["role_ids"] = [str(x) for x in body.role_ids]
    await audit_svc.record(
        db, action="user_updated", resource="user", tenant_id=u.tenant_id,
        user_id=user.id, resource_id=str(u.id),
        ip=request.client.host if request.client else None, detail=changed,
    )
    await db.commit()
    await db.refresh(u, ["roles"])
    return _user_out(u)


# ─── Roles & permissions ─────────────────────────────────────────────────────

@router.get("/roles", response_model=list[RoleOut],
            dependencies=[require_permission("role", "view")])
async def list_roles(user: ActiveUser, db: DB):
    q = select(Role).options(selectinload(Role.permissions), selectinload(Role.users))
    if not user.is_superadmin:
        # system (tenant_id is None) + own-tenant roles
        q = q.where((Role.tenant_id.is_(None)) | (Role.tenant_id == user.tenant_id))
    rows = (await db.execute(q.order_by(Role.is_system.desc(), Role.name))).scalars().all()
    return [
        RoleOut(
            id=r.id, name=r.name, is_system=r.is_system, tenant_id=r.tenant_id,
            permissions=[f"{p.resource}:{p.action}" for p in r.permissions],
            permission_ids=[p.id for p in r.permissions],
            user_count=len(r.users),
        ) for r in rows
    ]


@router.post("/roles", response_model=RoleOut,
             dependencies=[require_permission("role", "update")])
async def create_role(body: RoleCreate, user: ActiveUser, db: DB):
    if user.tenant_id is None and not user.is_superadmin:
        raise HTTPException(status_code=400, detail="tenant_context_required")
    role = Role(name=body.name, tenant_id=user.tenant_id, is_system=False)
    db.add(role)
    await db.commit()
    await db.refresh(role, ["permissions", "users"])
    return RoleOut(id=role.id, name=role.name, is_system=False, tenant_id=role.tenant_id)


@router.put("/roles/{role_id}/permissions", response_model=RoleOut,
            dependencies=[require_permission("role", "update")])
async def set_role_permissions(role_id: uuid.UUID, body: RolePermissions,
                               user: ActiveUser, db: DB, request: Request):
    role = (await db.execute(
        select(Role).where(Role.id == role_id).options(
            selectinload(Role.permissions), selectinload(Role.users))
    )).scalar_one_or_none()
    if role is None:
        raise HTTPException(status_code=404, detail="role_not_found")
    if role.is_system:
        raise HTTPException(status_code=403, detail="system_role_readonly")
    if not user.is_superadmin and role.tenant_id != user.tenant_id:
        raise HTTPException(status_code=404, detail="role_not_found")

    perms = (await db.execute(
        select(Permission).where(Permission.id.in_(body.permission_ids))
    )).scalars().all()
    role.permissions = list(perms)
    await audit_svc.record(
        db, action="role_permissions_set", resource="role", tenant_id=role.tenant_id,
        user_id=user.id, resource_id=str(role.id),
        ip=request.client.host if request.client else None,
        detail={"count": len(perms)},
    )
    await db.commit()
    await db.refresh(role, ["permissions", "users"])
    return RoleOut(
        id=role.id, name=role.name, is_system=role.is_system, tenant_id=role.tenant_id,
        permissions=[f"{p.resource}:{p.action}" for p in role.permissions],
        permission_ids=[p.id for p in role.permissions],
        user_count=len(role.users),
    )


@router.get("/permissions", response_model=list[PermissionOut],
            dependencies=[require_permission("role", "view")])
async def list_permissions(user: ActiveUser, db: DB):
    rows = (await db.execute(
        select(Permission).order_by(Permission.resource, Permission.action)
    )).scalars().all()
    return [PermissionOut(id=p.id, resource=p.resource, action=p.action,
                          description=p.description) for p in rows]


# ─── Audit log viewer ────────────────────────────────────────────────────────

@router.get("/audit", dependencies=[require_permission("audit", "view")])
async def list_audit(
    user: ActiveUser, db: DB,
    action: str | None = Query(default=None),
    resource: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
):
    q = select(AuditLog)
    tid = _tenant_filter(user)
    if tid is not None:
        q = q.where(AuditLog.tenant_id == tid)
    if action:
        q = q.where(AuditLog.action == action)
    if resource:
        q = q.where(AuditLog.resource == resource)
    rows = (await db.execute(
        q.order_by(AuditLog.created_at.desc()).limit(limit).offset(offset)
    )).scalars().all()

    # Resolve actor emails in one pass.
    uids = {r.user_id for r in rows if r.user_id}
    emails: dict[uuid.UUID, str] = {}
    if uids:
        for u in (await db.execute(select(User).where(User.id.in_(uids)))).scalars():
            emails[u.id] = u.email
    return [{
        "id": str(r.id), "action": r.action, "resource": r.resource,
        "resource_id": r.resource_id, "user_id": str(r.user_id) if r.user_id else None,
        "user_email": emails.get(r.user_id) if r.user_id else None,
        "ip": r.ip, "detail": r.detail,
        "created_at": r.created_at.isoformat() if r.created_at else None,
    } for r in rows]
