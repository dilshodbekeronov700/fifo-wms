import asyncio
import logging
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.health import snapshot as worker_heartbeats
from app.core.logging import configure_logging, init_sentry, request_id_ctx
from app.db.base import AsyncSessionLocal, Base, engine
from app.worker.key_refresh import run_key_refresh_worker
from app.worker.outbox_worker import run_outbox_worker
from app.worker.reservation_expiry import run_reservation_expiry_worker

configure_logging()
logger = logging.getLogger(__name__)
if init_sentry():
    logger.info("Sentry error tracking enabled")


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.DEBUG:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        # Auto-seed RBAC catalog + system roles in DEBUG. Must never block startup.
        try:
            from app.core.seed import seed_rbac
            from app.db.base import AsyncSessionLocal

            async with AsyncSessionLocal() as db:
                counts = await seed_rbac(db)
                await db.commit()
            logger.info("RBAC seeded: %s", counts)
        except Exception:
            logger.exception("RBAC auto-seed failed (continuing startup)")

    # Pull (Smartup'dan olish) endi VAQT JADVALI bilan emas — inson "Yangilash"
    # tugmasini bosganda (POST /connectors/smartup/pull) darhol bajariladi.
    # Shuning uchun run_sync_worker (cadensli pull) ishga TUSHIRILMAYDI.
    # Outbox worker QOLADI: u tasdiqlangan (manual-approve) push'larni yetkazadi.
    tasks = [
        asyncio.create_task(run_outbox_worker()),
        asyncio.create_task(run_key_refresh_worker()),
        asyncio.create_task(run_reservation_expiry_worker()),
    ]
    logger.info("Background workers started: outbox, key-refresh, reservation-expiry "
                "(pull = qo'lda 'Yangilash' orqali)")

    yield

    for t in tasks:
        t.cancel()
    for t in tasks:
        try:
            await t
        except asyncio.CancelledError:
            pass


app = FastAPI(
    title=settings.APP_NAME,
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 422 (schema) xatolarini batafsil loglaymiz — qaysi maydon noto'g'ri yuborilganini ko'rish uchun.
from fastapi.exceptions import RequestValidationError  # noqa: E402
from fastapi.responses import JSONResponse  # noqa: E402

@app.exception_handler(RequestValidationError)
async def _log_validation_error(request: Request, exc: RequestValidationError):
    try:
        body = (await request.body()).decode("utf-8", "replace")
    except Exception:
        body = "<unreadable>"
    logging.getLogger("validation").warning(
        "422 %s %s\n  errors=%s\n  body=%s",
        request.method, request.url.path, exc.errors(), body[:1000],
    )
    return JSONResponse(status_code=422, content={"detail": exc.errors()})


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request_id = request.headers.get("x-request-id") or uuid.uuid4().hex[:12]
    request.state.request_id = request_id
    token = request_id_ctx.set(request_id)   # loglarga correlation-id qo'shadi
    try:
        response = await call_next(request)
    finally:
        request_id_ctx.reset(token)
    response.headers["x-request-id"] = request_id
    # Xavfsizlik sarlavhalari (asosiy himoya).
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    return response


app.include_router(api_router)


@app.get("/health")
async def health():
    """Liveness — jarayon tirikligini tekshiradi (arzon, bog'liqliksiz)."""
    return {"status": "ok"}


@app.get("/health/ready")
async def readiness():
    """Readiness — DB va fon workerlar sog'ligini tekshiradi.

    Orkestrator (K8s/compose) shu endpointga qarab trafik yuboradimi yo'qmi
    hal qiladi. DB yetib bo'lmasa → 503; worker qotib qolsa → degraded.
    """
    checks: dict[str, object] = {}
    ok = True

    try:
        async with AsyncSessionLocal() as db:
            await db.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as exc:
        checks["database"] = f"error: {exc}"
        ok = False

    ages = worker_heartbeats()
    max_age = settings.WORKER_HEARTBEAT_MAX_AGE
    workers: dict[str, str] = {}
    for name, age in ages.items():
        fresh = age <= max_age
        workers[name] = "ok" if fresh else f"stale ({age:.0f}s)"
        if not fresh:
            ok = False
    checks["workers"] = workers

    status = "ok" if ok else "degraded"
    return JSONResponse(status_code=200 if ok else 503,
                        content={"status": status, "checks": checks})
