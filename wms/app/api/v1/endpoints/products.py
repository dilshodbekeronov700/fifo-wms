"""Product and Batch CRUD."""
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import ActiveUser, get_db, require_permission
from app.models.inventory import Batch, Product
from app.models.tenant import Tenant
from app.schemas.inventory import BatchCreate, BatchOut, ProductCreate, ProductOut, ProductUpdate

router = APIRouter(prefix="/products", tags=["products"])
DB = Annotated[AsyncSession, Depends(get_db)]


@router.post(
    "/",
    response_model=ProductOut,
    status_code=201,
    dependencies=[require_permission("product", "create")],
)
async def create_product(body: ProductCreate, user: ActiveUser, db: DB):
    if user.tenant_id is None:
        raise HTTPException(status_code=400, detail="Super-admin must specify tenant via admin endpoint")
    product = Product(tenant_id=user.tenant_id, **body.model_dump())
    db.add(product)
    await db.commit()
    await db.refresh(product)
    return product


@router.get("/", response_model=list[ProductOut])
async def list_products(user: ActiveUser, db: DB, include_inactive: bool = False):
    q = select(Product)
    if not include_inactive:
        q = q.where(Product.is_active.is_(True))
    if not user.is_superadmin:
        q = q.where(Product.tenant_id == user.tenant_id)
    result = await db.execute(q.order_by(Product.created_at))
    return result.scalars().all()


@router.get("/by-gtin", response_model=ProductOut)
async def get_product_by_gtin(user: ActiveUser, db: DB, gtin: str):
    """Resolve a product by GTIN (used by the TSD inventory-count flow)."""
    q = select(Product).where(Product.gtin == gtin)
    if not user.is_superadmin:
        q = q.where(Product.tenant_id == user.tenant_id)
    product = (await db.execute(q)).scalar_one_or_none()
    if product is None:
        raise HTTPException(status_code=404, detail=f"GTIN {gtin} not found")
    return product


@router.get("/{product_id}", response_model=ProductOut)
async def get_product(product_id: uuid.UUID, user: ActiveUser, db: DB):
    return await _get(product_id, user, db)


@router.patch(
    "/{product_id}",
    response_model=ProductOut,
    dependencies=[require_permission("product", "update")],
)
async def update_product(product_id: uuid.UUID, body: ProductUpdate, user: ActiveUser, db: DB):
    """Mahsulotni tahrirlaydi — faqat berilgan maydonlarni yangilaydi."""
    product = await _get(product_id, user, db)
    changes = body.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(product, field, value)
    await db.commit()
    await db.refresh(product)
    return product


@router.delete(
    "/{product_id}",
    dependencies=[require_permission("product", "delete")],
)
async def delete_product(product_id: uuid.UUID, user: ActiveUser, db: DB):
    """Soft-delete — mahsulotni o'chirmaydi, faqat nofaol qiladi (is_active=False)."""
    product = await _get(product_id, user, db)
    product.is_active = False
    await db.commit()
    return {"detail": "Mahsulot nofaol qilindi", "id": str(product_id)}


@router.post(
    "/{product_id}/batches",
    response_model=BatchOut,
    status_code=201,
    dependencies=[require_permission("batch", "create")],
)
async def create_batch(product_id: uuid.UUID, body: BatchCreate, user: ActiveUser, db: DB):
    await _get(product_id, user, db)
    batch = Batch(product_id=product_id, **body.model_dump())
    db.add(batch)
    await db.commit()
    await db.refresh(batch)
    return batch


@router.get("/{product_id}/batches", response_model=list[BatchOut])
async def list_batches(product_id: uuid.UUID, user: ActiveUser, db: DB):
    await _get(product_id, user, db)
    result = await db.execute(select(Batch).where(Batch.product_id == product_id))
    return result.scalars().all()


# ── Buxgalteriya Ocard 64 ta mahsulot to'plami ───────────────────────────────
# products.ts faylidan olingan — Green White kompaniyasining o'z mahsulotlari
_OCARD_PRODUCTS = [
    {"gtin": "08801104304047", "name": "Salqin kofe. Cafe Latte 0.35 l",           "uom": "unit"},
    {"gtin": "08801104306591", "name": "Salqin kofe. Vanilla Latte 0.35l",          "uom": "unit"},
    {"gtin": "08001620017661", "name": "Bellini alkogolsiz gazlangan 0.180 l",      "uom": "unit"},
    {"gtin": "08801104940238", "name": "Sutli ichimlik Qahva aromali 200 ml",       "uom": "unit"},
    {"gtin": "08801104940023", "name": "Sutli ichimlik Qulupnay aromali 200 ml",    "uom": "unit"},
    {"gtin": "00769828221591", "name": "Sutli ichimlik Banana aromali 200 ml",      "uom": "unit"},
    {"gtin": "08801104940146", "name": "Sutli ichimlik Qovunli aromali 200 ml",     "uom": "unit"},
    {"gtin": "08801104940931", "name": "Salqin kofe. Dolce Latte 0.35 l",           "uom": "unit"},
    {"gtin": "08005016380018", "name": "BELLINI ZERO shaftoli 0.75 ml",             "uom": "unit"},
    {"gtin": "24780094510325", "name": "Karlovy Vary gazlangan 0.5 l (GROUP)",      "uom": "unit"},
    {"gtin": "04780094510406", "name": "BLANC BLEU Dyushes 0.7 l",                  "uom": "unit"},
    {"gtin": "04780094510390", "name": "BLANC BLEU Moxito 0.5 l",                   "uom": "unit"},
    {"gtin": "04780094510369", "name": "BLANC BLEU Tarxun 0.7 l",                   "uom": "unit"},
    {"gtin": "04780094510383", "name": "BLANC BLEU Moxito 0.7 l",                   "uom": "unit"},
    {"gtin": "04780094510376", "name": "BLANC BLEU Tarxun 0.5 l",                   "uom": "unit"},
    {"gtin": "04780094510413", "name": "BLANC BLEU Dyushes 0.5 l",                  "uom": "unit"},
    {"gtin": "08801104944625", "name": "Salqin kofe. Americano 0.24 l",             "uom": "unit"},
    {"gtin": "08801104948005", "name": "Salqin kofe. Americano Decaf 0.35 l",       "uom": "unit"},
    {"gtin": "08801104212274", "name": "Salqin kofe. Cafe Latte 0.24 l",            "uom": "unit"},
    {"gtin": "08801104304023", "name": "Salqin kofe. Americano 0.35 l",             "uom": "unit"},
    {"gtin": "08801104212403", "name": "Salqin kofe. Macchiato 0.24 l",             "uom": "unit"},
    {"gtin": "08801104212397", "name": "Salqin kofe. Sweet Americano 0.24 l",       "uom": "unit"},
    {"gtin": "08801104212601", "name": "Salqin kofe. Vanila Latte 0.24 l",          "uom": "unit"},
    {"gtin": "24780094510332", "name": "Karlovy Vary gazlangan 0.33 l (GROUP)",     "uom": "unit"},
    {"gtin": "04780094510338", "name": "Karlovy Vary gazlangan 0.33 l",             "uom": "unit"},
    {"gtin": "04780094510321", "name": "Karlovy Vary gazlangan 0.5 l",              "uom": "unit"},
    {"gtin": "24780094510318", "name": "BLANC BLEU gazlangan 0.5 l (GROUP)",        "uom": "unit"},
    {"gtin": "34780094510070", "name": "Blanc Bleu gazsiz 0.5 l (GROUP)",           "uom": "unit"},
    {"gtin": "54780094510067", "name": "Blanc Bleu gazsiz 0.33 l (GROUP)",          "uom": "unit"},
    {"gtin": "24780094510301", "name": "BLANC BLEU gazlangan 0.33 l (GROUP)",       "uom": "unit"},
    {"gtin": "24780094510080", "name": "BLANC BLEU gazsiz 0.7 l (GROUP)",           "uom": "unit"},
    {"gtin": "24780094510073", "name": "BLANC BLEU gazsiz 0.5 l (GROUP)",           "uom": "unit"},
    {"gtin": "24780094510066", "name": "Blanc Bleu gazsiz 0.33 l (GROUP)",          "uom": "unit"},
    {"gtin": "34780094510056", "name": "Blanc Bleu gazsiz 0.25 l (GROUP)",          "uom": "unit"},
    {"gtin": "24780094510042", "name": "Blanc Bleu gazli 0.7 l (GROUP)",            "uom": "unit"},
    {"gtin": "24780094510035", "name": "Blanc Bleu gazli 0.5 l (GROUP)",            "uom": "unit"},
    {"gtin": "14780094510106", "name": "OCARD gazsiz 0.7 l (GROUP)",                "uom": "unit"},
    {"gtin": "34780094510025", "name": "Blanc Bleu gazli 0.33 l (GROUP)",           "uom": "unit"},
    {"gtin": "34780094510087", "name": "BLANC BLEU gazsiz 0.7 l (GROUP)",           "uom": "unit"},
    {"gtin": "34780094510018", "name": "Blanc Bleu gazli 0.25 l (GROUP)",           "uom": "unit"},
    {"gtin": "14780094510304", "name": "BLANC BLEU gazlangan 0.33 l (GROUP)",       "uom": "unit"},
    {"gtin": "04780094510093", "name": "Ichimlik suvi gazsiz 18.9 l",               "uom": "unit"},
    {"gtin": "34780094510032", "name": "Blanc Bleu gazli 0.5 l (GROUP)",            "uom": "unit"},
    {"gtin": "54780094510012", "name": "Blanc Bleu gazli 0.25 l (GROUP)",           "uom": "unit"},
    {"gtin": "54780094510050", "name": "Blanc Bleu gazsiz 0.25 l (GROUP)",          "uom": "unit"},
    {"gtin": "54780094510029", "name": "Blanc Bleu gazli 0.33 l (GROUP)",           "uom": "unit"},
    {"gtin": "34780094510049", "name": "Blanc Bleu gazlangan 0.7 l (GROUP)",        "uom": "unit"},
    {"gtin": "04780094510109", "name": "OCARD gazsiz 0.7 l",                        "uom": "unit"},
    {"gtin": "04780094510291", "name": "Ichimlik suvi gazsiz 10 l",                 "uom": "unit"},
    {"gtin": "08005016381312", "name": "Zero rozegold alkogolsiz 0.75 l",           "uom": "unit"},
    {"gtin": "08005016381213", "name": "Zero ruby alkogolsiz 0.75 l",               "uom": "unit"},
    {"gtin": "08801104671101", "name": "Sutli ichimlik Vanilla aromali 200 ml",     "uom": "unit"},
    {"gtin": "08005016381411", "name": "Zero Gold alkogolsiz 0.75 l",               "uom": "unit"},
    {"gtin": "04780094510284", "name": "Ichimlik suvi gazsiz 5 l",                  "uom": "unit"},
    {"gtin": "04780094510017", "name": "BLANC BLEU gazli 0.25 l",                   "uom": "unit"},
    {"gtin": "04780094510307", "name": "BLANC BLEU gazlangan 0.33 l",               "uom": "unit"},
    {"gtin": "04780094510314", "name": "BLANC BLEU gazlangan 0.5 l",                "uom": "unit"},
    {"gtin": "04780094510062", "name": "BLANC BLEU gazsiz 0.33 l",                  "uom": "unit"},
    {"gtin": "04780094510024", "name": "BLANC BLEU gazli 0.33 l",                   "uom": "unit"},
    {"gtin": "04780094510086", "name": "BLANC BLEU gazsiz 0.7 l",                   "uom": "unit"},
    {"gtin": "04780094510055", "name": "BLANC BLEU gazsiz 0.25 l",                  "uom": "unit"},
    {"gtin": "04780094510048", "name": "BLANC BLEU gazli 0.7 l",                    "uom": "unit"},
    {"gtin": "04780094510031", "name": "BLANC BLEU gazli 0.5 l",                    "uom": "unit"},
    {"gtin": "04780094510079", "name": "Blanc Bleu gazsiz 0.5 l",                   "uom": "unit"},
]


@router.post(
    "/seed-ocard",
    dependencies=[require_permission("product", "create")],
)
async def seed_ocard_products(user: ActiveUser, db: DB):
    """Buxgalteriya Ocard'dagi 64 ta Green White mahsulotini WMS'ga seed qiladi.

    Mavjud GTIN bo'lsa nomini yangilaydi, yo'q bo'lsa yangi yozuv qo'shadi.
    Tenant-specific — faqat joriy tenant uchun ishlaydi.
    """
    # Superadmin uchun birinchi aktiv tenantni olamiz
    tenant_id = user.tenant_id
    if tenant_id is None:
        first = (await db.execute(
            select(Tenant).where(Tenant.is_active.is_(True)).limit(1)
        )).scalar_one_or_none()
        if first is None:
            raise HTTPException(status_code=400, detail="Tenant topilmadi — avval tenant yarating")
        tenant_id = first.id

    created = updated = 0
    for item in _OCARD_PRODUCTS:
        gtin = item["gtin"]
        name_uz = item["name"]
        # Bir xil GTIN bo'yicha bir nechta yozuv bo'lishi mumkin (unikal cheklov yo'q),
        # shuning uchun scalar_one_or_none() emas — birinchisini olamiz.
        matches = (await db.execute(
            select(Product).where(
                Product.tenant_id == tenant_id,
                Product.gtin == gtin,
            )
        )).scalars().all()
        existing = matches[0] if matches else None

        if existing is None:
            db.add(Product(
                tenant_id=tenant_id,
                gtin=gtin,
                uom=item.get("uom", "unit"),
                name={"uz": name_uz, "ru": name_uz},
                category="beverages",
            ))
            created += 1
        else:
            # Nomini va kategoriyasini yangilaymiz (qolganlarni saqlaymiz)
            prev_ru = existing.name.get("ru") if isinstance(existing.name, dict) else None
            existing.name = {"uz": name_uz, "ru": prev_ru or name_uz}
            existing.category = existing.category or "beverages"
            updated += 1

    await db.commit()
    return {
        "message": "Ocard mahsulotlari seed qilindi",
        "total": len(_OCARD_PRODUCTS),
        "created": created,
        "updated": updated,
    }


async def _get(product_id: uuid.UUID, user: ActiveUser, db: AsyncSession) -> Product:
    q = select(Product).where(Product.id == product_id)
    if not user.is_superadmin:
        q = q.where(Product.tenant_id == user.tenant_id)
    result = await db.execute(q)
    p = result.scalar_one_or_none()
    if p is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return p
