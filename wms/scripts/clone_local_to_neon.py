"""Lokal Postgres → Neon to'liq klon (bir martalik migratsiya).

Lokal bazadagi BARCHA app jadvallarini (tenant, user, ombor, zona, 606 yacheyka,
mahsulot, stok, KIZ, ledger…) Neon'ga aynan ko'chiradi. UUID'lar saqlanadi, tenant
remap shart emas — login ham bir xil (admin@wms.uz / admin123).

Ishlatish:
  SRC="postgresql://wms:wms@localhost:5432/wms" \
  DST="postgresql://neondb_owner:PASS@HOST/neondb?sslmode=require" \
  poetry run python -m scripts.clone_local_to_neon
"""
import asyncio
import json
import os
from urllib.parse import parse_qsl, urlsplit, urlunsplit

import asyncpg

import app.models  # noqa: F401 — register metadata
from app.db.base import Base


def _split(url: str):
    """asyncpg tushunmaydigan query paramlarni (sslmode/channel_binding) ajratadi."""
    url = url.replace("+asyncpg", "")
    p = urlsplit(url)
    q = dict(parse_qsl(p.query))
    sslmode = q.pop("sslmode", None)
    q.pop("channel_binding", None)
    clean = urlunsplit((p.scheme, p.netloc, p.path, "", ""))
    return clean, sslmode not in (None, "disable"), ("-pooler" in p.netloc)


async def _connect(url: str):
    clean, ssl, pooler = _split(url)
    kw = {}
    if ssl:
        kw["ssl"] = True
    if pooler:
        kw["statement_cache_size"] = 0
    conn = await asyncpg.connect(clean, timeout=30, **kw)
    for t in ("json", "jsonb"):
        await conn.set_type_codec(t, encoder=json.dumps, decoder=json.loads, schema="pg_catalog")
    return conn


async def main() -> None:
    src_url = os.environ["SRC"]
    dst_url = os.environ["DST"]
    src = await _connect(src_url)
    dst = await _connect(dst_url)

    # FK-xavfsiz tartib (metadata bo'yicha). alembic_version tegilmaydi.
    tables = [t.name for t in Base.metadata.sorted_tables]

    # 1) Neon'ni tozalash (teskari tartibda), tenant/user/hammasi qayta klonlanadi.
    for name in reversed(tables):
        await dst.execute(f'TRUNCATE TABLE "{name}" RESTART IDENTITY CASCADE')
    print(f"Neon tozalandi ({len(tables)} jadval)")

    # 2) Har jadvalni ko'chirish (to'g'ri tartibda).
    total = 0
    for name in tables:
        rows = await src.fetch(f'SELECT * FROM "{name}"')
        if not rows:
            print(f"  {name}: 0")
            continue
        cols = list(rows[0].keys())
        collist = ", ".join(f'"{c}"' for c in cols)
        ph = ", ".join(f"${i+1}" for i in range(len(cols)))
        stmt = f'INSERT INTO "{name}" ({collist}) VALUES ({ph})'
        await dst.executemany(stmt, [tuple(r[c] for c in cols) for r in rows])
        total += len(rows)
        print(f"  {name}: {len(rows)}")

    await src.close()
    await dst.close()
    print(f"✓ Klon tugadi — jami {total} qator Neon'ga ko'chirildi")


if __name__ == "__main__":
    asyncio.run(main())
