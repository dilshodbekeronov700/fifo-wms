"""
Directed putaway (slotting) — Swiss-watch precision, 20+ factor weighted scoring.

World-class WMS practice: every empty/partial location is first screened by HARD
constraints (it must physically be able to hold the goods), then ranked by a
weighted sum of SOFT factors. Weights and zone-acceptance rules are
admin-configurable from the UI; travel distances come from the 2D-map
coordinates; congestion/velocity come from the immutable ledger; temperature
suitability comes from IoT sensors. The full per-factor breakdown is returned so
the operator (and the manager) can see *why* a slot was chosen — explainable
slotting, not a black box.

HARD CONSTRAINTS (a location failing any of these is excluded entirely):
  - zone not blocked and accepts the product (admin putaway_rules)
  - zone is a storage zone (not staging/dock/quarantine/return)
  - location active and not BLOCKED
  - free capacity remains after existing stock AND pending reservations
  - mixing rule: if the zone disallows mixing, the slot must be empty or already
    hold the *same* product+batch
  - weight headroom: estimated load weight must fit max_weight_kg

SOFT FACTORS (each normalised 0..1, multiplied by an admin weight, then summed):
   1 zone_match            zone type matches the product's ABC preference
   2 consolidation         same SKU already stored here (reduce fragmentation)
   3 fefo                  same batch/expiry already here (FEFO grouping)
   4 batch_purity          no *different* batch present (protects FEFO integrity)
   5 capacity_fit          the qty fits the remaining capacity snugly
   6 empty_preference      full pallet → empty slot; partial → partial slot
   7 dock_proximity        near the shipping dock, scaled by ABC velocity
   8 inbound_proximity     short travel from the receiving/staging area
   9 golden_zone           ergonomic pick tier for fast (A) movers
  10 weight_tier           heavy product → ground tier
  11 weight_capacity_fit   weight headroom remaining
  12 cube_utilization      product volume fits the slot volume well
  13 accessibility         lower position / aisle-end = easier to reach
  14 rack_group_affinity   same SKU/category already in this rack block
  15 category_block        slot's block is dedicated to the product category
  16 aisle_balance         spread load across racks (avoid congestion)
  17 velocity_match        ledger heatmap: fast SKU → high-throughput slot
  18 temperature_ok        IoT: the zone's sensor reading is within range
  19 expiry_urgency        near-expiry goods → easy-pick accessible slot
  20 reservation_clear     prefer slots with no competing pending reservation
  21 single_sku_bonus      keep a location pure (one SKU) when possible
  22 open_pallet_routing   open/partial pallet → OPEN_PALLET zone near picking
"""
from __future__ import annotations

import math
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.inventory import AbcClass, Product, StockItem
from app.models.ledger import LedgerEntry
from app.models.reservation import PutawayReservation, ReservationStatus
from app.models.sensor import Sensor
from app.models.warehouse import Location, LocationStatus, Zone, ZoneType


@dataclass
class SlottingCandidate:
    location: Location
    zone: Zone
    score: float
    reason: str
    factors: dict[str, float] = field(default_factory=dict)   # weighted contribution per factor
    remaining_boxes: int = 0


# Default weights — also the *schema* surfaced to the admin UI (every key here is
# editable per-tenant via Tenant.settings["slotting_weights"]).
DEFAULT_WEIGHTS: dict[str, float] = {
    "zone_match": 30.0,
    "consolidation": 25.0,
    "fefo": 18.0,
    "batch_purity": 8.0,
    "capacity_fit": 10.0,
    "empty_preference": 6.0,
    "dock_proximity": 20.0,
    "inbound_proximity": 8.0,
    "golden_zone": 10.0,
    # Vazn va o'lcham omillari o'chirildi (0) — hozircha mantiqsiz, ma'lumot to'liq emas.
    # Keyinroq mahsulotlarga vazn/o'lcham kiritilsa, qiymatni qaytarish kifoya.
    "weight_tier": 0.0,
    "weight_capacity_fit": 0.0,
    "cube_utilization": 0.0,
    "accessibility": 5.0,
    "rack_group_affinity": 14.0,
    "category_block": 10.0,
    "aisle_balance": 7.0,
    "velocity_match": 9.0,
    "temperature_ok": 15.0,
    "expiry_urgency": 8.0,
    "reservation_clear": 6.0,
    "single_sku_bonus": 5.0,
    "open_pallet_routing": 8.0,
    # Maxsus zona klassifikatsiyasi (GTIN/muddat/СТМ) — mos mahsulotni o'z
    # maxsus yacheykasiga KUCHLI yo'naltiradi (foydalanuvchi so'rovi).
    "classification_match": 35.0,
}


def load_weights(tenant_settings: dict | None) -> dict[str, float]:
    """Merge admin-configured slotting weights over DEFAULT_WEIGHTS.

    Only known weight keys are honoured; unknown keys are ignored so
    DEFAULT_WEIGHTS stays the canonical schema. A weight of 0 disables a factor.
    """
    merged = dict(DEFAULT_WEIGHTS)
    custom = (tenant_settings or {}).get("slotting_weights") or {}
    for key in DEFAULT_WEIGHTS:
        val = custom.get(key)
        if isinstance(val, (int, float)):
            merged[key] = float(val)
    return merged


# ABC velocity multiplier for dock proximity (A movers strongly prefer near-dock).
_ABC_VELOCITY = {AbcClass.A: 1.0, AbcClass.B: 0.6, AbcClass.C: 0.3, None: 0.5}

ZONE_ABC_PREF: dict[AbcClass | None, list[ZoneType]] = {
    AbcClass.A: [ZoneType.PICK, ZoneType.OPEN_PALLET],
    AbcClass.B: [ZoneType.PICK, ZoneType.RESERVE],
    AbcClass.C: [ZoneType.RESERVE],
    None: [ZoneType.RESERVE, ZoneType.PICK],
}

# Zones a product is never auto-placed into.
_NON_STORAGE = {ZoneType.STAGING, ZoneType.DOCK, ZoneType.QUARANTINE, ZoneType.RETURN}

_VELOCITY_WINDOW_DAYS = 30


def _norm_gtin(g: str | None) -> str:
    """GTIN normalizatsiya — faqat raqamlar (taqqoslash uchun)."""
    return "".join(ch for ch in (g or "") if ch.isdigit())


def zone_accepts(
    zone: Zone,
    product: Product,
    *,
    gtin: str | None = None,
    days_to_expiry: int | None = None,
) -> bool:
    """Evaluate admin-defined putaway_rules for this zone/product (HARD).

    Kengaytirilgan klassifikatsiya (foydalanuvchi so'rovi):
      - blocked / manual_only  → zona auto-joylashdan chiqariladi
      - abc / categories / product_ids / volume  → mavjud filtrlar
      - gtin_allowlist / gtin_blocklist  → aniq GTIN(lar) uchun/emas (СТМ, maxsus mahsulot)
      - expiry_max_days  → faqat shu kun ichida muddati tugaydigan (muddati o'tgan/yaqin) mahsulot
    """
    rules = zone.putaway_rules or {}
    if rules.get("blocked") or rules.get("manual_only"):
        return False
    abc = rules.get("abc")
    if abc and (product.abc_class is None or product.abc_class.value not in abc):
        return False
    cats = rules.get("categories")
    if cats and (product.category is None or product.category not in cats):
        return False
    pids = rules.get("product_ids")
    if pids and str(product.id) not in pids:
        return False
    vmin, vmax = rules.get("min_volume_m3"), rules.get("max_volume_m3")
    if vmin is not None and (product.volume_m3 is None or product.volume_m3 < vmin):
        return False
    if vmax is not None and (product.volume_m3 is None or product.volume_m3 > vmax):
        return False
    # GTIN allow/block (СТМ / maxsus mahsulot yacheykasi)
    pg = _norm_gtin(gtin or getattr(product, "gtin", None))
    allow = rules.get("gtin_allowlist")
    if allow and pg not in {_norm_gtin(g) for g in allow}:
        return False
    block = rules.get("gtin_blocklist")
    if block and pg in {_norm_gtin(g) for g in block}:
        return False
    # Muddat filtri (muddati o'tgan/yaqin mahsulot yacheykasi)
    exp_max = rules.get("expiry_max_days")
    if exp_max is not None:
        if days_to_expiry is None or days_to_expiry > exp_max:
            return False
    return True


def zone_classification_match(
    zone: Zone,
    product: Product,
    *,
    gtin: str | None = None,
    days_to_expiry: int | None = None,
) -> bool:
    """Zona shu mahsulotni MAXSUS nishonga olganmi (GTIN allowlist / muddat filtri)?
    True bo'lsa — classification_match bonus beriladi (kuchli yo'naltirish)."""
    rules = zone.putaway_rules or {}
    pg = _norm_gtin(gtin or getattr(product, "gtin", None))
    allow = rules.get("gtin_allowlist")
    if allow and pg and pg in {_norm_gtin(g) for g in allow}:
        return True
    exp_max = rules.get("expiry_max_days")
    if exp_max is not None and days_to_expiry is not None and days_to_expiry <= exp_max:
        return True
    return False


def _capacity_boxes(loc: Location, product: Product) -> int:
    """Total box capacity of a slot (pallets × boxes/pallet, default 50)."""
    pallets = loc.max_pallets or 1
    bpp = product.boxes_per_pallet or 50
    return max(1, pallets * bpp)


def _days_to_expiry(expiry_date: str | None) -> int | None:
    if not expiry_date:
        return None
    try:
        d = date.fromisoformat(expiry_date[:10])
    except ValueError:
        return None
    return (d - datetime.now(timezone.utc).date()).days


async def suggest_locations(
    db: AsyncSession,
    *,
    warehouse_id: uuid.UUID,
    product: Product,
    batch_id: uuid.UUID | None = None,
    expiry_date: str | None = None,
    qty: int = 1,
    unit_count: int = 0,
    pallet_open: bool = False,
    top_n: int = 5,
    weights: dict[str, float] | None = None,
    tenant_settings: dict | None = None,
) -> list[SlottingCandidate]:
    """Rank candidate slots by the 22-factor weighted model (see module docstring)."""
    if weights is not None:
        w = {**DEFAULT_WEIGHTS, **weights}
    else:
        w = load_weights(tenant_settings)

    # 1. Candidate storage locations (+ their zones)
    rows = (await db.execute(
        select(Location, Zone)
        .join(Zone, Zone.id == Location.zone_id)
        .where(
            Zone.warehouse_id == warehouse_id,
            Location.is_active.is_(True),
            Location.status.in_([LocationStatus.EMPTY, LocationStatus.PARTIAL]),
            Zone.is_active.is_(True),
            Zone.zone_type.not_in(_NON_STORAGE),
        )
    )).all()
    if not rows:
        return []

    # 2. Reference points: dock centres (out) and staging/receiving centres (in)
    zone_pts = (await db.execute(
        select(Zone).where(
            Zone.warehouse_id == warehouse_id, Zone.is_active.is_(True),
        )
    )).scalars().all()
    docks = [(z.x, z.y) for z in zone_pts
             if z.zone_type == ZoneType.DOCK and z.x is not None and z.y is not None]
    inbounds = [(z.x, z.y) for z in zone_pts
                if z.zone_type == ZoneType.STAGING and z.x is not None and z.y is not None]

    # 3. Existing stock per location (all SKUs — needed for mixing + occupancy)
    stock_by_loc: dict[uuid.UUID, list[StockItem]] = {}
    for s in (await db.execute(
        select(StockItem).where(StockItem.warehouse_id == warehouse_id)
    )).scalars():
        stock_by_loc.setdefault(s.location_id, []).append(s)

    # 3b. Rack-groups (blocks) that already hold this product — for block affinity.
    product_rack_groups: set[str] = {
        rg for (rg,) in (await db.execute(
            select(Location.rack_group)
            .join(StockItem, StockItem.location_id == Location.id)
            .where(
                StockItem.warehouse_id == warehouse_id,
                StockItem.product_id == product.id,
                Location.rack_group.is_not(None),
            )
            .distinct()
        )).all() if rg
    }

    # 4. Pending reservations per location (capacity is held by these too)
    reserved_boxes: dict[uuid.UUID, int] = {}
    for loc_id, boxes in (await db.execute(
        select(PutawayReservation.location_id, func.coalesce(func.sum(PutawayReservation.qty), 0))
        .where(
            PutawayReservation.warehouse_id == warehouse_id,
            PutawayReservation.status == ReservationStatus.PENDING,
        )
        .group_by(PutawayReservation.location_id)
    )).all():
        reserved_boxes[loc_id] = int(boxes or 0)

    # 5. Velocity heatmap — putaway/pick activity per location over the window
    since = datetime.now(timezone.utc) - timedelta(days=_VELOCITY_WINDOW_DAYS)
    move_count: dict[uuid.UUID, int] = {}
    for loc_id, cnt in (await db.execute(
        select(LedgerEntry.to_location_id, func.count())
        .where(
            LedgerEntry.warehouse_id == warehouse_id,
            LedgerEntry.created_at >= since,
            LedgerEntry.to_location_id.is_not(None),
        )
        .group_by(LedgerEntry.to_location_id)
    )).all():
        if loc_id is not None:
            move_count[loc_id] = int(cnt)
    max_moves = max(move_count.values()) if move_count else 0

    # 6. IoT temperature alert state per zone (penalise out-of-range zones)
    zone_temp_alert: dict[uuid.UUID, bool] = {}
    for sensor in (await db.execute(
        select(Sensor).where(
            Sensor.warehouse_id == warehouse_id,
            Sensor.is_active.is_(True),
            Sensor.zone_id.is_not(None),
        )
    )).scalars():
        t = sensor.last_temp
        alert = t is not None and (
            (sensor.temp_min is not None and t < sensor.temp_min)
            or (sensor.temp_max is not None and t > sensor.temp_max)
        )
        # any alerting sensor flags the zone
        zone_temp_alert[sensor.zone_id] = zone_temp_alert.get(sensor.zone_id, False) or alert

    preferred = ZONE_ABC_PREF.get(product.abc_class, ZONE_ABC_PREF[None])
    velocity = _ABC_VELOCITY.get(product.abc_class, 0.5)
    days_exp = _days_to_expiry(expiry_date)
    est_unit_weight = product.weight_kg or 0.0
    est_load_weight = est_unit_weight * (unit_count or 0)

    # Pre-compute normalised distances (dock + inbound) and rack congestion.
    dock_d, in_d = {}, {}
    rack_load: dict[tuple, int] = {}
    for loc, zone in rows:
        if loc.x is not None and loc.y is not None:
            if docks:
                dock_d[loc.id] = min(math.hypot(loc.x - dx, loc.y - dy) for dx, dy in docks)
            if inbounds:
                in_d[loc.id] = min(math.hypot(loc.x - ix, loc.y - iy) for ix, iy in inbounds)
        key = (zone.id, loc.row, loc.rack)
        occupied = 1 if stock_by_loc.get(loc.id) else 0
        rack_load[key] = rack_load.get(key, 0) + occupied

    def _norm(d: dict[uuid.UUID, float]) -> tuple[float, float]:
        if not d:
            return 0.0, 1.0
        lo, hi = min(d.values()), max(d.values())
        return lo, (hi - lo) or 1.0
    dock_lo, dock_rng = _norm(dock_d)
    in_lo, in_rng = _norm(in_d)

    candidates: list[SlottingCandidate] = []
    for loc, zone in rows:
        # ── HARD CONSTRAINTS ────────────────────────────────────────────────
        if not zone_accepts(zone, product, gtin=getattr(product, "gtin", None), days_to_expiry=days_exp):
            continue
        existing = stock_by_loc.get(loc.id, [])
        occupied_boxes = sum(s.qty for s in existing)
        cap = _capacity_boxes(loc, product)
        remaining = cap - occupied_boxes - reserved_boxes.get(loc.id, 0)
        if remaining <= 0:
            continue  # no room (stock + reservations fill it)

        # mixing rule
        same_only = all(
            s.product_id == product.id and (batch_id is None or s.batch_id == batch_id)
            for s in existing
        )
        if existing and not zone.allow_mixed and not same_only:
            continue  # zone forbids mixing and a different SKU/batch is here

        # weight headroom (hard)
        if loc.max_weight_kg and est_load_weight and est_load_weight > loc.max_weight_kg * 1.001:
            continue

        # ── SOFT FACTORS ────────────────────────────────────────────────────
        f: dict[str, float] = {}
        reasons: list[str] = []
        same_sku = any(s.product_id == product.id for s in existing)
        same_batch = any(
            s.product_id == product.id and batch_id is not None and s.batch_id == batch_id
            for s in existing
        )
        diff_batch = any(
            s.product_id == product.id and batch_id is not None and s.batch_id != batch_id
            for s in existing
        )

        # 0 classification_match — maxsus zona (GTIN/muddat/СТМ) mos mahsulotni tortadi
        if zone_classification_match(zone, product, gtin=getattr(product, "gtin", None), days_to_expiry=days_exp):
            f["classification_match"] = w["classification_match"]
            reasons.append("maxsus zona mos")
        # 1 zone_match
        if zone.zone_type in preferred:
            f["zone_match"] = w["zone_match"]
            reasons.append(f"zona={zone.zone_type.value}")
        # 2 consolidation
        if same_sku:
            f["consolidation"] = w["consolidation"]
            reasons.append("SKU jamlash")
        # 3 fefo
        if same_batch:
            f["fefo"] = w["fefo"]
            reasons.append("partiya jamlash")
        # 4 batch_purity (no different batch)
        if not diff_batch:
            f["batch_purity"] = w["batch_purity"]
        # 5 capacity_fit — snug fit (qty close to remaining without overflow)
        fit = min(qty, remaining) / remaining if remaining else 0
        f["capacity_fit"] = w["capacity_fit"] * fit
        # 6 empty_preference
        if pallet_open:
            if loc.status == LocationStatus.PARTIAL:
                f["empty_preference"] = w["empty_preference"]
        elif loc.status == LocationStatus.EMPTY:
            f["empty_preference"] = w["empty_preference"]
        # 7 dock_proximity (velocity scaled)
        if loc.id in dock_d:
            prox = 1.0 - (dock_d[loc.id] - dock_lo) / dock_rng
            f["dock_proximity"] = w["dock_proximity"] * prox * velocity
            if prox > 0.66:
                reasons.append("dokga yaqin")
        # 8 inbound_proximity (short putaway travel)
        if loc.id in in_d:
            iprox = 1.0 - (in_d[loc.id] - in_lo) / in_rng
            f["inbound_proximity"] = w["inbound_proximity"] * iprox
        # 9 golden_zone (ergonomic tier for A movers)
        if loc.tier is not None and product.abc_class == AbcClass.A and loc.tier <= 2:
            f["golden_zone"] = w["golden_zone"] * (1.0 if loc.tier == 1 else 0.7)
        # 10 weight_tier (heavy → ground)
        if est_unit_weight > 15 and loc.tier is not None:
            if loc.tier <= 1:
                f["weight_tier"] = w["weight_tier"]
                reasons.append("og'ir→past yarus")
        # 11 weight_capacity_fit
        if loc.max_weight_kg and est_load_weight:
            head = max(0.0, 1.0 - est_load_weight / loc.max_weight_kg)
            f["weight_capacity_fit"] = w["weight_capacity_fit"] * head
        # 12 cube_utilization
        if product.volume_m3 and all(
            v for v in (loc.length_mm, loc.width_mm, loc.height_mm)
        ):
            slot_m3 = (loc.length_mm * loc.width_mm * loc.height_mm) / 1e9
            if slot_m3 > 0:
                util = min(1.0, (product.volume_m3 * qty) / slot_m3)
                f["cube_utilization"] = w["cube_utilization"] * util
        # 13 accessibility (lower position number = easier)
        if loc.position is not None:
            f["accessibility"] = w["accessibility"] * (1.0 / (1.0 + loc.position))
        # 14 rack_group_affinity (same SKU already in this rack block)
        if loc.rack_group and loc.rack_group in product_rack_groups:
            f["rack_group_affinity"] = w["rack_group_affinity"]
            reasons.append("bir blokda jamlash")
        # 15 category_block (slot block dedicated to the product category)
        cats = (zone.putaway_rules or {}).get("categories")
        if cats and product.category and product.category in cats:
            f["category_block"] = w["category_block"]
        # 16 aisle_balance (penalise congested racks)
        key = (zone.id, loc.row, loc.rack)
        load = rack_load.get(key, 0)
        f["aisle_balance"] = w["aisle_balance"] * (1.0 / (1.0 + load))
        # 17 velocity_match (heatmap)
        if max_moves and product.abc_class in (AbcClass.A, AbcClass.B):
            mv = move_count.get(loc.id, 0) / max_moves
            f["velocity_match"] = w["velocity_match"] * mv
        # 18 temperature_ok (penalise alerting zones to ~0)
        if zone.id in zone_temp_alert:
            f["temperature_ok"] = 0.0 if zone_temp_alert[zone.id] else w["temperature_ok"]
            if zone_temp_alert[zone.id]:
                reasons.append("⚠ harorat chegaradan tashqari")
        # 19 expiry_urgency (near-expiry → accessible)
        if days_exp is not None and days_exp < 90:
            ease = 1.0 if (loc.tier or 9) <= 1 else 0.4
            urgency = max(0.0, 1.0 - days_exp / 90)
            f["expiry_urgency"] = w["expiry_urgency"] * urgency * ease
            if days_exp < 30:
                reasons.append(f"muddat {days_exp}k → tez terish")
        # 20 reservation_clear (no competing reservation)
        if reserved_boxes.get(loc.id, 0) == 0:
            f["reservation_clear"] = w["reservation_clear"]
        # 21 single_sku_bonus (keep pure)
        if not existing or same_only:
            f["single_sku_bonus"] = w["single_sku_bonus"]
        # 22 open_pallet_routing
        if pallet_open and zone.zone_type == ZoneType.OPEN_PALLET:
            f["open_pallet_routing"] = w["open_pallet_routing"]
            reasons.append("ochiq-pallet zonasi")

        score = round(sum(f.values()), 2)
        candidates.append(
            SlottingCandidate(
                location=loc, zone=zone, score=score,
                reason=", ".join(reasons) or "standart",
                factors={k: round(v, 2) for k, v in f.items() if v},
                remaining_boxes=remaining,
            )
        )

    candidates.sort(key=lambda c: c.score, reverse=True)
    return candidates[:top_n]
