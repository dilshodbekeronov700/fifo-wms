"""Fresh-deploy schema init.

0001_baseline `Base.metadata.create_all` bilan BUTUN joriy sxemani yaratadi, shuning
uchun 0002+ migratsiyalari toza bazada takrorlanib to'qnashadi. Deployда migratsiya
zanjirini yugurtirish o'rniga: create_all (idempotent, checkfirst) + keyin start.sh
`alembic stamp head` bilan versiyani belgilaydi. Kelajakdagi migratsiyalar normal ishlaydi.
"""
import asyncio

import app.models  # noqa: F401 — registers all models on metadata
from app.db.base import Base, engine


async def main() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()
    print("✓ Schema ensured (create_all, idempotent)")


if __name__ == "__main__":
    asyncio.run(main())
