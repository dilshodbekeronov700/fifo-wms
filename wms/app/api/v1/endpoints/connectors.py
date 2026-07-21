"""
Tenant connector configuration endpoints (tenant-admin only).

Credentials are entered through the UI and stored ENCRYPTED at rest. The set of
connectors and their form fields come from the connector registry, so adding a
new ERP/TMS surfaces in the UI automatically.

GET    /connectors/specs        — Available connector types + form schema (UI)
POST   /connectors              — Create / update a connector (encrypts secrets)
GET    /connectors              — List configured connectors (no secrets)
DELETE /connectors/{type}       — Disable a connector
POST   /connectors/{type}/test  — Probe connectivity with stored credentials
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import app.connectors.registry  # noqa: F401 — populates the connector registry
from app.connectors.base import all_specs, describe, get_spec, validate_credentials
from app.core.crypto import decrypt_credentials, encrypt_credentials
from app.core.deps import ActiveUser, get_db, require_permission
from app.models.connector import ConnectorConfig
from app.models.inventory import OutboxMessage, OutboxStatus
from app.services import outbox as outbox_svc
from sqlalchemy import func

router = APIRouter(prefix="/connectors", tags=["connectors"])
DB = Annotated[AsyncSession, Depends(get_db)]


class ConnectorUpsert(BaseModel):
    connector_type: str
    credentials: dict
    settings: dict = {}


@router.get("/specs", dependencies=[require_permission("connector", "view")])
async def list_specs() -> list[dict]:
    """Form schema for every registered connector — drives the UI."""
    return [describe(s) for s in all_specs()]


@router.post(
    "/",
    status_code=201,
    dependencies=[require_permission("connector", "create")],
)
async def upsert_connector(body: ConnectorUpsert, user: ActiveUser, db: DB):
    if user.tenant_id is None:
        raise HTTPException(status_code=400, detail="Tenant context required")

    try:
        get_spec(body.connector_type)
    except KeyError:
        raise HTTPException(status_code=422, detail=f"Unknown connector: {body.connector_type}")

    missing = validate_credentials(body.connector_type, body.credentials)
    if missing:
        raise HTTPException(
            status_code=422,
            detail=f"Missing required fields for {body.connector_type}: {missing}",
        )

    encrypted = encrypt_credentials(body.credentials)

    result = await db.execute(
        select(ConnectorConfig).where(
            ConnectorConfig.tenant_id == user.tenant_id,
            ConnectorConfig.connector_type == body.connector_type,
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        existing.credentials = encrypted
        existing.settings = body.settings
        existing.is_active = True
        cfg = existing
    else:
        cfg = ConnectorConfig(
            tenant_id=user.tenant_id,
            connector_type=body.connector_type,
            credentials=encrypted,
            settings=body.settings,
        )
        db.add(cfg)

    await db.commit()
    await db.refresh(cfg)
    return {"id": str(cfg.id), "connector_type": cfg.connector_type, "status": "configured"}


@router.get("/", dependencies=[require_permission("connector", "view")])
async def list_connectors(user: ActiveUser, db: DB) -> list[dict]:
    if user.tenant_id is None:
        raise HTTPException(status_code=400, detail="Tenant context required")

    result = await db.execute(
        select(ConnectorConfig).where(ConnectorConfig.tenant_id == user.tenant_id)
    )
    configs = result.scalars().all()
    out: list[dict] = []
    for c in configs:
        # Expose only non-secret field values so the form can be re-populated.
        spec = None
        try:
            spec = get_spec(c.connector_type)
        except KeyError:
            pass
        non_secret: dict = {}
        if spec:
            creds = decrypt_credentials(c.credentials)
            non_secret = {
                f.name: creds.get(f.name)
                for f in spec.fields
                if not f.secret and creds.get(f.name) is not None
            }
        out.append({
            "id": str(c.id),
            "connector_type": c.connector_type,
            "is_active": c.is_active,
            "has_credentials": bool(c.credentials),
            "values": non_secret,
        })
    return out


@router.delete(
    "/{connector_type}",
    dependencies=[require_permission("connector", "delete")],
)
async def disable_connector(connector_type: str, user: ActiveUser, db: DB):
    if user.tenant_id is None:
        raise HTTPException(status_code=400, detail="Tenant context required")

    result = await db.execute(
        select(ConnectorConfig).where(
            ConnectorConfig.tenant_id == user.tenant_id,
            ConnectorConfig.connector_type == connector_type,
        )
    )
    cfg = result.scalar_one_or_none()
    if cfg is None:
        raise HTTPException(status_code=404, detail="Connector not found")

    cfg.is_active = False
    await db.commit()
    return {"detail": f"{connector_type} connector disabled"}


def _parse_retry_after_secs(retry_after: str | None) -> int | None:
    """Retry-After sarlavhasidan sekundlarni ajratadi (HTTP-sana qo'llab-quvvatlanmaydi)."""
    if not retry_after:
        return None
    try:
        secs = int(float(retry_after.strip()))
    except (ValueError, AttributeError):
        return None
    return secs if secs > 0 else None


def _retry_after_hint(retry_after: str | None) -> str:
    """Retry-After (soniya yoki HTTP-sana) ni o'qiluvchan o'zbekcha matnga aylantiradi."""
    default = " Bir necha soniyadan keyin qayta urinib ko'ring."
    secs = _parse_retry_after_secs(retry_after)
    if not secs:
        return default
    if secs < 60:
        return f" ~{secs} soniyadan keyin qayta urinib ko'ring."
    if secs < 3600:
        return f" ~{secs // 60} daqiqadan keyin qayta urinib ko'ring."
    return f" ~{round(secs / 3600, 1)} soatdan keyin qayta urinib ko'ring."


@router.post(
    "/{connector_type}/test",
    dependencies=[require_permission("connector", "view")],
)
async def test_connector(connector_type: str, user: ActiveUser, db: DB):
    """Build the client from stored (encrypted) credentials and run its probe."""
    if user.tenant_id is None:
        raise HTTPException(status_code=400, detail="Tenant context required")

    try:
        spec = get_spec(connector_type)
    except KeyError:
        raise HTTPException(status_code=422, detail=f"Unknown connector: {connector_type}")

    result = await db.execute(
        select(ConnectorConfig).where(
            ConnectorConfig.tenant_id == user.tenant_id,
            ConnectorConfig.connector_type == connector_type,
            ConnectorConfig.is_active.is_(True),
        )
    )
    cfg = result.scalar_one_or_none()
    if cfg is None:
        raise HTTPException(status_code=404, detail="Connector not configured")

    if spec.test is None:
        return {"status": "unknown", "connector": connector_type, "detail": "No probe defined"}

    # 429 cooldown: oldingi urinish chegaraga uchragan bo'lsa, oyna tugaguncha
    # tashqi API'ni QAYTA chaqirmaymiz — aks holda kvota yana sarflanadi.
    cooldown_until = (cfg.settings or {}).get("_test_cooldown_until")
    if cooldown_until:
        try:
            until = datetime.fromisoformat(cooldown_until)
            remaining = (until - datetime.now(timezone.utc)).total_seconds()
        except (ValueError, TypeError):
            remaining = 0
        if remaining > 0:
            return {
                "status": "rate_limited",
                "connector": connector_type,
                "detail": f"So'rovlar chegarasiga yetilgan edi — kalit yaroqli.{_retry_after_hint(str(int(remaining)))}",
            }

    try:
        creds = decrypt_credentials(cfg.credentials)
        client = spec.builder(creds, cfg.settings or {})
        await spec.test(client)
        # Muvaffaqiyat — eski cooldownni tozalaymiz.
        if (cfg.settings or {}).get("_test_cooldown_until"):
            new_settings = {**(cfg.settings or {})}
            new_settings.pop("_test_cooldown_until", None)
            cfg.settings = new_settings
            await db.commit()
        return {"status": "ok", "connector": connector_type}
    except httpx.HTTPStatusError as exc:
        # HTTP javob keldi — kalit yaroqsizligini so'rov chegarasidan ajratamiz.
        code = exc.response.status_code
        if code == 429:
            retry_after = exc.response.headers.get("Retry-After")
            # Oynani saqlaymiz (24 soatdan oshmasin), keyingi chaqiruvlarni to'xtatish uchun.
            secs = _parse_retry_after_secs(retry_after)
            if secs:
                until = datetime.now(timezone.utc) + timedelta(seconds=min(secs, 86400))
                cfg.settings = {**(cfg.settings or {}), "_test_cooldown_until": until.isoformat()}
                await db.commit()
            return {
                "status": "rate_limited",
                "connector": connector_type,
                "detail": f"So'rovlar chegarasiga yetildi (429) — kalit yaroqli, lekin hozir tekshirib bo'lmadi.{_retry_after_hint(retry_after)}",
            }
        if code in (401, 403):
            return {
                "status": "error",
                "connector": connector_type,
                "detail": f"Avtorizatsiya rad etildi ({code}) — API kalit yaroqsiz yoki muddati o'tgan.",
            }
        if code >= 500:
            return {
                "status": "error",
                "connector": connector_type,
                "detail": f"Tashqi xizmat xatosi ({code}) — Asl Belgisi tomonida vaqtincha nosozlik. Keyinroq urinib ko'ring.",
            }
        return {
            "status": "error",
            "connector": connector_type,
            "detail": f"HTTP {code}: {exc.response.text[:200]}",
        }
    except Exception as exc:
        return {"status": "error", "connector": connector_type, "detail": str(exc)}


@router.post(
    "/smartup/sync/products",
    dependencies=[require_permission("connector", "update")],
)
async def sync_smartup_products(user: ActiveUser, db: DB, full: bool = False):
    """Pull SKU master data from Smartup into WMS Products (incremental by default)."""
    if user.tenant_id is None:
        raise HTTPException(status_code=400, detail="Tenant context required")

    from app.core.connector_factory import get_smartup_client
    from app.services import sync as sync_svc

    cfg = (await db.execute(
        select(ConnectorConfig).where(
            ConnectorConfig.tenant_id == user.tenant_id,
            ConnectorConfig.connector_type == "smartup",
            ConnectorConfig.is_active.is_(True),
        )
    )).scalar_one_or_none()
    if cfg is None:
        raise HTTPException(status_code=404, detail="Smartup connector not configured")

    settings_data = dict(cfg.settings or {})
    begin = None if full else settings_data.get("last_product_sync")

    client = await get_smartup_client(db, user.tenant_id)
    result = await sync_svc.sync_products(
        db, tenant_id=user.tenant_id, client=client, begin_modified_on=begin
    )

    settings_data["last_product_sync"] = sync_svc.now_iso()
    cfg.settings = settings_data
    await db.commit()

    return {
        "fetched": result.fetched,
        "created": result.created,
        "updated": result.updated,
        "last_product_sync": settings_data["last_product_sync"],
    }


@router.post(
    "/aslbelgisi/sync/products",
    dependencies=[require_permission("connector", "update")],
)
async def sync_aslbelgisi_products(user: ActiveUser, db: DB):
    """Asl Belgisi product-registry dan mahsulotlarni WMS'ga sync qiladi."""
    if user.tenant_id is None:
        raise HTTPException(status_code=400, detail="Tenant context required")

    from app.core.connector_factory import get_aslbelgisi_client
    from app.services import sync as sync_svc

    client = await get_aslbelgisi_client(db, user.tenant_id)
    result = await sync_svc.sync_aslbelgisi_products(
        db, tenant_id=user.tenant_id, client=client
    )
    await db.commit()
    return result


@router.get(
    "/aslbelgisi/product-card",
    dependencies=[require_permission("connector", "view")],
)
async def aslbelgisi_product_card(user: ActiveUser, db: DB, gtin: str):
    """Asl Belgisi mahsulot-reyestr kartochkasi (GTIN bo'yicha) — nom, status,
    qadoq turi, kategoriya, TNVED, ishlab chiqaruvchi. UI'da katta modalда ko'rsatiladi."""
    if user.tenant_id is None:
        raise HTTPException(status_code=400, detail="Tenant context required")
    from app.core.connector_factory import get_aslbelgisi_client

    def _loc(v):
        if isinstance(v, dict):
            return v.get("name") if isinstance(v.get("name"), dict) else v
        return v

    try:
        client = await get_aslbelgisi_client(db, user.tenant_id)
        products = await client.search_product_by_gtin(gtin, limit=3)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Asl Belgisi: {exc}")
    if not products:
        return {"found": False, "gtin": gtin}
    p = products[0]
    image = None
    try:
        if p.get("id"):
            detail = await client.get_product_detail(p["id"])
            for fid in client.photo_files(detail)[:6]:  # birinchi ishlaganini olamiz
                try:
                    got = await client.get_product_file_b64(fid)
                except Exception:
                    continue
                if got:
                    b64, mime = got
                    image = f"data:{mime};base64,{b64}"
                    break
    except Exception:
        image = None
    return {
        "found": True,
        "gtin": p.get("gtin") or gtin,
        "id": p.get("id"),
        "image": image,
        "product_name": p.get("productName") or p.get("name"),
        "status": _loc(p.get("status")),
        "status_value": (p.get("status") or {}).get("value") if isinstance(p.get("status"), dict) else p.get("status"),
        "package_type": _loc(p.get("packageType")),
        "product_category": p.get("productCategory"),
        "tnved": p.get("tnved"),
        "producer": p.get("participantName"),
        "inn": p.get("inn"),
        "product_group": p.get("pg"),
        "count": len(products),
    }


@router.get("/status", dependencies=[require_permission("connector", "view")])
async def integration_status(user: ActiveUser, db: DB):
    """Integratsiya holati paneli — connectorlar + outbox navbat + sync vaqtlari."""
    if user.tenant_id is None:
        raise HTTPException(status_code=400, detail="Tenant context required")

    cfgs = (await db.execute(
        select(ConnectorConfig).where(ConnectorConfig.tenant_id == user.tenant_id)
    )).scalars().all()

    # Outbox navbat statistikasi (connector × status)
    rows = (await db.execute(
        select(OutboxMessage.connector, OutboxMessage.status, func.count())
        .where(OutboxMessage.tenant_id == user.tenant_id)
        .group_by(OutboxMessage.connector, OutboxMessage.status)
    )).all()
    queue: dict[str, dict[str, int]] = {}
    for connector, status, cnt in rows:
        queue.setdefault(connector, {})[status.value] = cnt

    # Oxirgi xato push'lar
    failed = (await db.execute(
        select(OutboxMessage.connector, OutboxMessage.event_type, OutboxMessage.last_error,
               OutboxMessage.attempts, OutboxMessage.updated_at)
        .where(OutboxMessage.tenant_id == user.tenant_id,
               OutboxMessage.status == OutboxStatus.FAILED)
        .order_by(OutboxMessage.updated_at.desc()).limit(10)
    )).all()

    connectors = []
    for c in cfgs:
        s = c.settings or {}
        connectors.append({
            "type": c.connector_type,
            "is_active": c.is_active,
            "last_product_sync": s.get("last_product_sync"),
            "last_balance_sync": s.get("last_balance_sync"),
            # Per-flow avto-pull vaqtlari (Faza 3 worker yozadi)
            "sync_times": {
                "products": s.get("last_product_sync"),   # eski kalit (birlik)
                "orders": s.get("last_orders_sync"),
                "inputs": s.get("last_inputs_sync"),
                "reconciliation": s.get("last_reconciliation_sync"),
            },
            # Pull snapshot'lari (yengil ko'rinish: nechta order/input kutmoqda)
            "snapshots": {
                "orders": s.get("orders_snapshot"),
                "inputs": s.get("inputs_snapshot"),
            },
            # Oxirgi svereka xulosasi (Faza 3 reconciliation worker yozadi)
            "reconciliation": s.get("last_reconciliation"),
            "queue": queue.get(c.connector_type, {}),
        })

    # Operator tasdig'i kutayotgan push'lar (qo'lda-push navbati)
    pending = await outbox_svc.list_pending_approval(db, tenant_id=user.tenant_id)

    return {
        "connectors": connectors,
        "queue": queue,
        "pending_approval": [
            {
                "id": str(m.id),
                "event_type": m.event_type,
                "connector": m.connector,
                "created_at": m.created_at.isoformat() if m.created_at else None,
                "payload": {k: v for k, v in (m.payload or {}).items()
                            if not k.startswith("_")},
            }
            for m in pending
        ],
        "recent_failures": [
            {"connector": f.connector, "event_type": f.event_type,
             "error": (f.last_error or "")[:200], "attempts": f.attempts,
             "at": f.updated_at.isoformat() if f.updated_at else None}
            for f in failed
        ],
    }


# ── Qo'lda "Yangilash" — Smartup'dan DARHOL pull (vaqt jadvalisiz) ──────────────
class PullBody(BaseModel):
    flows: list[str] | None = None   # None → barchasi (orders, inputs, products, reconciliation)


@router.post(
    "/smartup/pull",
    dependencies=[require_permission("connector", "view")],
)
async def pull_smartup_now(user: ActiveUser, db: DB, body: PullBody | None = None):
    """Inson 'Yangilash' bosganda Smartup'dan ma'lumotni darhol tortadi."""
    if user.tenant_id is None:
        raise HTTPException(status_code=400, detail="Tenant context required")
    from app.worker.sync_worker import pull_now
    flows = body.flows if body else None
    try:
        results = await pull_now(db, tenant_id=user.tenant_id, flows=flows)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"results": results}


@router.get(
    "/smartup/reconciliation",
    dependencies=[require_permission("connector", "view")],
)
async def smartup_reconciliation(user: ActiveUser, db: DB, warehouse_id: uuid.UUID):
    """WMS ↔ Smartup qoldiq sverekasi (jonli) — Qoldiqlar sahifasidagi 'ERP svereka' tabi."""
    if user.tenant_id is None:
        raise HTTPException(status_code=400, detail="Tenant context required")
    from app.core.connector_factory import get_smartup_client
    from app.services.reconciliation import run_reconciliation
    try:
        client = await get_smartup_client(db, user.tenant_id)
    except Exception:
        client = None
    report = await run_reconciliation(
        db, tenant_id=user.tenant_id, warehouse_id=warehouse_id, smartup_client=client,
    )
    return report


# ── Qo'lda-push: operator tasdig'i navbati ──────────────────────────────────────
class RejectBody(BaseModel):
    reason: str = ""


@router.get(
    "/smartup/push/pending",
    dependencies=[require_permission("connector", "view")],
)
async def list_push_pending(user: ActiveUser, db: DB):
    """Tasdiq kutayotgan WMS→Smartup push xabarlari."""
    if user.tenant_id is None:
        raise HTTPException(status_code=400, detail="Tenant context required")
    msgs = await outbox_svc.list_pending_approval(db, tenant_id=user.tenant_id)
    return [
        {
            "id": str(m.id),
            "event_type": m.event_type,
            "created_at": m.created_at.isoformat() if m.created_at else None,
            "payload": {k: v for k, v in (m.payload or {}).items()
                        if not k.startswith("_")},
        }
        for m in msgs
    ]


@router.post(
    "/smartup/push/{msg_id}/approve",
    dependencies=[require_permission("connector", "update")],
)
async def approve_push(msg_id: uuid.UUID, user: ActiveUser, db: DB):
    if user.tenant_id is None:
        raise HTTPException(status_code=400, detail="Tenant context required")
    msg = await outbox_svc.approve(db, msg_id=msg_id, tenant_id=user.tenant_id, user_id=user.id)
    if msg is None:
        raise HTTPException(status_code=404, detail="Tasdiq kutayotgan xabar topilmadi")
    await db.commit()
    return {"id": str(msg.id), "status": "approved"}


@router.post(
    "/smartup/push/{msg_id}/reject",
    dependencies=[require_permission("connector", "update")],
)
async def reject_push(msg_id: uuid.UUID, body: RejectBody, user: ActiveUser, db: DB):
    if user.tenant_id is None:
        raise HTTPException(status_code=400, detail="Tenant context required")
    msg = await outbox_svc.reject(
        db, msg_id=msg_id, tenant_id=user.tenant_id, user_id=user.id, reason=body.reason
    )
    if msg is None:
        raise HTTPException(status_code=404, detail="Tasdiq kutayotgan xabar topilmadi")
    await db.commit()
    return {"id": str(msg.id), "status": "rejected"}


# ── ERP-yozuv ruxsati (rol asosida, sozlanadigan) ────────────────────────────
from app.models.auth import Role  # noqa: E402
from app.services import erp_policy as erp_pol  # noqa: E402


class ErpPolicyBody(BaseModel):
    allowed_roles: list[str]


@router.get("/erp-policy", dependencies=[require_permission("connector", "view")])
async def get_erp_policy(user: ActiveUser, db: DB) -> dict:
    """Qaysi rollar Smartup'ga YOZA oladi + joriy foydalanuvchi yoza oladimi."""
    if user.tenant_id is None:
        raise HTTPException(status_code=400, detail="Tenant context required")
    allowed = await erp_pol.get_erp_write_roles(db, user.tenant_id)
    all_roles = (await db.execute(
        select(Role.name).where(
            (Role.tenant_id == user.tenant_id) | (Role.tenant_id.is_(None))
        )
    )).scalars().all()
    return {
        "allowed_roles": allowed,
        "all_roles": sorted(set(all_roles)),
        "can_write": erp_pol.user_can_write_erp(user, allowed),
    }


@router.put("/erp-policy", dependencies=[require_permission("connector", "update")])
async def set_erp_policy(body: ErpPolicyBody, user: ActiveUser, db: DB) -> dict:
    if user.tenant_id is None:
        raise HTTPException(status_code=400, detail="Tenant context required")
    try:
        saved = await erp_pol.set_erp_write_roles(db, user.tenant_id, body.allowed_roles)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"allowed_roles": saved}


# ── Smartup sklad hujjatlari (read-only ko'rinish): ko'chirish, inventarizatsiya ──
from app.core.connector_factory import get_smartup_client as _get_su_client  # noqa: E402
from app.models.warehouse import Warehouse as _WH  # noqa: E402
from app.services import documents as _doc_svc  # noqa: E402


async def _wh_codes(db, tenant_id, warehouse_id):
    wh = await db.get(_WH, warehouse_id)
    if wh is None or wh.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Sklad topilmadi")
    return _doc_svc.warehouse_filter(wh.smartup_warehouse_code)


@router.get("/smartup/movements", dependencies=[require_permission("connector", "view")])
async def smartup_movements(user: ActiveUser, db: DB, warehouse_id: uuid.UUID) -> dict:
    """Smartup ichki (mkw) + tashkilotlararo (mfm) ko'chirishlar — read-only snapshot."""
    if user.tenant_id is None:
        raise HTTPException(status_code=400, detail="Tenant context required")
    codes = await _wh_codes(db, user.tenant_id, warehouse_id)
    client = await _get_su_client(db, user.tenant_id)
    internal = await client.get_movements(warehouse_codes=codes)
    cross = await client.get_cross_org_movements(warehouse_codes=codes)
    return {"internal": internal, "cross_org": cross,
            "count": len(internal) + len(cross)}


@router.get("/smartup/stocktakings", dependencies=[require_permission("connector", "view")])
async def smartup_stocktakings(user: ActiveUser, db: DB, warehouse_id: uuid.UUID) -> dict:
    """Smartup inventarizatsiyalar (stocktaking$export) — read-only snapshot."""
    if user.tenant_id is None:
        raise HTTPException(status_code=400, detail="Tenant context required")
    codes = await _wh_codes(db, user.tenant_id, warehouse_id)
    client = await _get_su_client(db, user.tenant_id)
    rows = await client.get_stocktakings(warehouse_codes=codes)
    return {"count": len(rows), "stocktakings": rows}


@router.get("/smartup/current-org", dependencies=[require_permission("connector", "view")])
async def smartup_current_org(user: ActiveUser, db: DB) -> dict:
    """Integratsiya HOZIR qaysi Smartup tashkilotiga ulangani — bitta buyurtmadan
    `filial_id`/`filial_code` o'qib qaytaradi (Sozlamalarda ko'rsatish uchun)."""
    if user.tenant_id is None:
        raise HTTPException(status_code=400, detail="Tenant context required")
    client = await _get_su_client(db, user.tenant_id)

    async def _sample(with_code: bool) -> dict:
        """Bitta urinish: filial_code bilan yoki bo'sh — qaysi org ulanishini aniqlaydi."""
        saved = client.filial_code
        if not with_code:
            client.filial_code = ""
        try:
            orders = await client.get_orders(statuses=None)
            return {
                "ok": True,
                "order_count": len(orders),
                "sample_customers": [o.customer_name for o in orders[:5] if o.customer_name],
            }
        except Exception as exc:
            return {"ok": False, "error": f"{exc}"}
        finally:
            client.filial_code = saved

    cfg = (await db.execute(
        select(ConnectorConfig).where(
            ConnectorConfig.tenant_id == user.tenant_id,
            ConnectorConfig.connector_type == "smartup",
        )
    )).scalar_one_or_none()
    creds = decrypt_credentials(cfg.credentials) if cfg else {}
    configured_code = creds.get("filial_code") or ""

    with_code = await _sample(bool(configured_code))
    result: dict = {
        "filial_id_header": creds.get("filial_id"),
        "filial_code": configured_code or "(bo'sh)",
        "note": "Org konteksti Smartup'da o'zgarishi mumkin — mijoz nomlari bilan tekshiring.",
    }
    if with_code["ok"]:
        result["sample_order_count"] = with_code["order_count"]
        result["sample_customers"] = with_code["sample_customers"]
        return result

    # filial_code bilan xato → bo'sh code bilan diagnostika (header yolg'iz qaysi org'ga boradi).
    result["filial_code_error"] = with_code["error"]
    result["fallback_no_code"] = await _sample(False)
    raise HTTPException(status_code=502, detail={
        "message": f"Smartup: {with_code['error']}",
        "diagnostics": result,
    })


@router.get("/smartup/writeoffs", dependencies=[require_permission("connector", "view")])
async def smartup_writeoffs(user: ActiveUser, db: DB, warehouse_id: uuid.UUID) -> dict:
    """Smartup spisaniyelar (writeoff$export) — read-only snapshot."""
    if user.tenant_id is None:
        raise HTTPException(status_code=400, detail="Tenant context required")
    codes = await _wh_codes(db, user.tenant_id, warehouse_id)
    client = await _get_su_client(db, user.tenant_id)
    rows = await client.get_writeoffs(warehouse_codes=codes)
    return {"count": len(rows), "writeoffs": rows}


@router.get("/smartup/returns", dependencies=[require_permission("connector", "view")])
async def smartup_returns(user: ActiveUser, db: DB, warehouse_id: uuid.UUID) -> dict:
    """Smartup qaytarishlar — sotuvdan (mijozdan) + ta'minotchiga. read-only."""
    if user.tenant_id is None:
        raise HTTPException(status_code=400, detail="Tenant context required")
    codes = await _wh_codes(db, user.tenant_id, warehouse_id)
    client = await _get_su_client(db, user.tenant_id)
    sale = await client.get_sale_returns(warehouse_codes=codes)
    supplier = await client.get_supplier_returns(warehouse_codes=codes)
    return {"sale": sale, "supplier": supplier, "count": len(sale) + len(supplier)}
