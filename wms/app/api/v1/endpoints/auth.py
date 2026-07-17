import hashlib
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.deps import ActiveUser, get_db
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.auth import RefreshToken, User
from app.models.tenant import Tenant
from app.schemas.auth import (
    LoginRequest, RefreshRequest, SignupRequest, TokenResponse, UserOut,
)
from app.services import audit as audit_svc

router = APIRouter(prefix="/auth", tags=["auth"])
DB = Annotated[AsyncSession, Depends(get_db)]


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, request: Request, db: DB):
    ip = request.client.host if request.client else None
    request_id = getattr(request.state, "request_id", None)
    now = datetime.now(timezone.utc)
    invalid = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
    )

    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    # Lockout check
    if user is not None and user.locked_until is not None:
        locked_until = user.locked_until
        if locked_until.tzinfo is None:
            locked_until = locked_until.replace(tzinfo=timezone.utc)
        if locked_until > now:
            await audit_svc.record(
                db, action="login_locked", resource="user",
                tenant_id=user.tenant_id, user_id=user.id, resource_id=str(user.id),
                ip=ip, request_id=request_id,
            )
            await db.commit()
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Account temporarily locked. Try again later.",
            )

    if (
        user is None
        or not user.is_active
        or not verify_password(body.password, user.hashed_password)
    ):
        if user is not None:
            user.failed_login_attempts += 1
            if user.failed_login_attempts >= settings.LOGIN_MAX_ATTEMPTS:
                user.locked_until = now + timedelta(minutes=settings.LOGIN_LOCKOUT_MINUTES)
                user.failed_login_attempts = 0
            await audit_svc.record(
                db, action="login_failed", resource="user",
                tenant_id=user.tenant_id, user_id=user.id, resource_id=str(user.id),
                ip=ip, request_id=request_id,
            )
            await db.commit()
        raise invalid

    # Self sign-up approval gate — valid credentials but awaiting admin approval.
    if not user.is_approved:
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="account_pending_approval",
        )

    # Success — reset counters
    user.failed_login_attempts = 0
    user.locked_until = None

    access = create_access_token(
        subject=str(user.id),
        extra={"tenant_id": str(user.tenant_id) if user.tenant_id else None},
    )
    refresh_raw, refresh_hash = create_refresh_token(subject=str(user.id))
    db.add(RefreshToken(user_id=user.id, token_hash=refresh_hash))
    await audit_svc.record(
        db, action="login", resource="user",
        tenant_id=user.tenant_id, user_id=user.id, resource_id=str(user.id),
        ip=ip, request_id=request_id,
    )
    await db.commit()

    return TokenResponse(access_token=access, refresh_token=refresh_raw)


@router.post("/signup", status_code=status.HTTP_201_CREATED)
async def signup(body: SignupRequest, request: Request, db: DB):
    """Self-registration → creates an unapproved account awaiting admin approval.

    The user picks the organisation (tenant) by its slug. The account cannot log
    in until an admin approves it and assigns a role (see /admin/users/*).
    """
    ip = request.client.host if request.client else None
    tenant = (await db.execute(
        select(Tenant).where(Tenant.slug == body.tenant_slug, Tenant.is_active.is_(True))
    )).scalar_one_or_none()
    if tenant is None:
        raise HTTPException(status_code=404, detail="organisation_not_found")

    exists = (await db.execute(select(User).where(User.email == body.email))).scalar_one_or_none()
    if exists is not None:
        raise HTTPException(status_code=409, detail="email_taken")

    user = User(
        tenant_id=tenant.id,
        email=body.email,
        phone=body.phone,
        full_name=body.full_name,
        hashed_password=hash_password(body.password),
        is_active=True,
        is_approved=False,        # ← awaits admin approval
        is_superadmin=False,
    )
    db.add(user)
    await db.flush()
    await audit_svc.record(
        db, action="signup", resource="user",
        tenant_id=tenant.id, user_id=user.id, resource_id=str(user.id),
        ip=ip, request_id=getattr(request.state, "request_id", None),
        detail={"email": body.email, "full_name": body.full_name},
    )
    await db.commit()
    return {"detail": "pending_approval", "user_id": str(user.id)}


@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: RefreshRequest, db: DB):
    exc = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
    try:
        payload = decode_token(body.refresh_token)
    except JWTError:
        raise exc

    if payload.get("type") != "refresh":
        raise exc

    token_hash = hashlib.sha256(body.refresh_token.encode()).hexdigest()
    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.token_hash == token_hash, RefreshToken.is_revoked.is_(False)
        )
    )
    db_token = result.scalar_one_or_none()
    if db_token is None:
        raise exc

    # Rotate: revoke old, issue new pair
    db_token.is_revoked = True

    user_result = await db.execute(select(User).where(User.id == db_token.user_id))
    user = user_result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise exc

    access = create_access_token(
        subject=str(user.id),
        extra={"tenant_id": str(user.tenant_id) if user.tenant_id else None},
    )
    refresh_raw, refresh_hash = create_refresh_token(subject=str(user.id))
    db.add(RefreshToken(user_id=user.id, token_hash=refresh_hash))
    await db.commit()

    return TokenResponse(access_token=access, refresh_token=refresh_raw)


@router.post("/logout")
async def logout(user: ActiveUser, body: RefreshRequest, db: DB):
    token_hash = hashlib.sha256(body.refresh_token.encode()).hexdigest()
    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.token_hash == token_hash, RefreshToken.user_id == user.id
        )
    )
    db_token = result.scalar_one_or_none()
    if db_token:
        db_token.is_revoked = True
        await db.commit()
    return {"detail": "Logged out"}


@router.get("/me", response_model=UserOut)
async def me(user: ActiveUser):
    return UserOut(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        tenant_id=user.tenant_id,
        is_superadmin=user.is_superadmin,
        roles=[r.name for r in user.roles],
    )
