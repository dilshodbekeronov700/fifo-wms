from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, mapped_column
from sqlalchemy import DateTime, func
import uuid
from datetime import datetime
from typing import Annotated

from app.core.config import settings

# SQLite (test) uchun pool sozlamalari qo'llanmaydi; Postgres (asyncpg) uchun
# concurrency + uzoq turgan ulanishlarni sog'lom saqlash (pre_ping) kerak.
_engine_kwargs: dict = {"echo": settings.DEBUG, "connect_args": settings.db_connect_args}
if not settings.DATABASE_URL.startswith("sqlite"):
    _engine_kwargs.update(
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW,
        pool_timeout=settings.DB_POOL_TIMEOUT,
        pool_pre_ping=True,       # tarqalgan/o'lik ulanishlarni ishlatishdan oldin tekshiradi
        pool_recycle=1800,        # 30 daqiqadan keyin ulanishni yangilaydi
    )

# db_url_clean — Neon/Supabase'ning sslmode/channel_binding paramlari olib
# tashlangan URL; SSL connect_args orqali beriladi (asyncpg mos).
engine = create_async_engine(settings.db_url_clean, **_engine_kwargs)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


# Reusable column type aliases
intpk = Annotated[int, mapped_column(primary_key=True, autoincrement=True)]
uuidpk = Annotated[uuid.UUID, mapped_column(primary_key=True, default=uuid.uuid4)]
created_at = Annotated[
    datetime, mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
]
updated_at = Annotated[
    datetime,
    mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    ),
]


async def get_db() -> AsyncSession:  # type: ignore[return]
    """Request-scoped session. Rolls back on any unhandled error so a failed
    request never leaves a half-applied transaction; callers commit explicitly."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
