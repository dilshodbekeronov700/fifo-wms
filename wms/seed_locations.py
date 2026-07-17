"""
Sklad GP — real yacheykalarni yaratish (PDF layout: warehouseLayout.ts bilan bir xil).
6 qator / 90 katak / har katak 2 pallet × 3 etaj = 540 yacheyka.
19L segmentlar → "Rezerv 19L" zonasi, 0.5L → "Pick 0.5L" zonasi.
"""
import asyncio
import uuid
from sqlalchemy import delete, select

from app.db.base import AsyncSessionLocal
from app.models.warehouse import Zone, Location, LocationType, LocationStatus

WAREHOUSE_ID = uuid.UUID("55ea743b-f340-49e9-961f-79c7720d739f")
ZONE_19L = uuid.UUID("c80eb144-0d88-44aa-9414-b620513f6ccd")   # Rezerv 19L
ZONE_05L = uuid.UUID("7094e18b-ece1-402b-9fe1-6e15c524bad7")   # Pick 0.5L

CELL_W = 1.95
ROW_D = 1.15
TIERS = 3
POSITIONS = 2

# warehouseLayout.ts dagi segmentlar bilan bir xil
SEGMENTS = [
    # id,    row,   block, x,    y,    cols, deep, product
    ("A",   "Q-1", "A", 0.5,  0.4,  16, 1, "19L"),
    ("B-L", "Q-2", "B", 0.5,  3.7,  9,  2, "0.5L"),
    ("B-R", "Q-2", "B", 21.0, 3.7,  6,  2, "0.5L"),
    ("C-L", "Q-4", "C", 0.5,  8.4,  9,  2, "0.5L"),
    ("C-R", "Q-4", "C", 21.0, 8.4,  6,  2, "0.5L"),
    ("D-L", "Q-6", "D", 3.0,  13.4, 7,  1, "19L"),
    ("D-R", "Q-6", "D", 22.0, 13.4, 7,  1, "19L"),
]


async def main():
    async with AsyncSessionLocal() as db:
        # 1. Eski yacheykalarni o'chirish (shu skladdagi)
        zones = (await db.execute(
            select(Zone.id).where(Zone.warehouse_id == WAREHOUSE_ID)
        )).scalars().all()
        if zones:
            await db.execute(delete(Location).where(Location.zone_id.in_(zones)))
        await db.commit()

        # 2. Yangi yacheykalarni yaratish
        count = 0
        for seg_id, row, block, x0, y0, cols, deep, product in SEGMENTS:
            zone_id = ZONE_19L if product == "19L" else ZONE_05L
            for r in range(deep):
                for c in range(cols):
                    cell_x = x0 + c * CELL_W
                    cell_y = y0 + r * ROW_D
                    cell_id = f"{seg_id}-{c + 1:02d}" + (f"-{r + 1}" if deep == 2 else "")
                    for t in range(1, TIERS + 1):
                        for p in range(1, POSITIONS + 1):
                            db.add(Location(
                                zone_id=zone_id,
                                code=cell_id,                       # map cell_id bo'yicha qidiradi
                                barcode=f"{cell_id}-T{t}-P{p}",     # unikal
                                location_type=LocationType.PALLET,
                                status=LocationStatus.EMPTY,
                                row=row,
                                rack=c + 1,
                                tier=t,
                                position=p,
                                x=cell_x,
                                y=cell_y,
                                max_pallets=1,
                            ))
                            count += 1
        await db.commit()
        print(f"Yaratildi: {count} yacheyka ({len(SEGMENTS)} segment)")


if __name__ == "__main__":
    asyncio.run(main())
