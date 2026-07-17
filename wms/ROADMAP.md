# WMS — Roadmap (0 → World-class)

**Mahsulot:** Bulutli SaaS WMS — Smartup ERP + Asl Belgisi (xtrace) + Android TSD bilan integratsiyalashgan.
**Birinchi mijoz:** Green White suv zavodi (19L + 0.5L tayyor mahsulot skladi).
**Asoslar:** Ledger = haqiqat manbai · konnektorlar plagin (ERP/TMS/marking almashtiriladi) · multi-tenant · API-first · offline TSD · UI'dan sozlanadigan.

Holat belgilari: ✅ tayyor · 🟡 qisman/jarayonda · ⬜ rejada

---

## Joriy holat (snapshot)

✅ Yadro skeleti: FastAPI, async SQLAlchemy, JWT auth+refresh, RBAC (eager-load bug tuzatildi), Ledger modeli, tenant/sklad/zona/yacheyka/SKU/batch/MC modellari, outbox.
✅ Kengaytiriluvchan konnektor qatlami: registr (`base.py`/`registry.py`), Fernet shifrlash (`crypto.py`), UI'dan kalit kiritish (`/connectors` + `/connectors/specs`), `test` probe.
✅ Asl Belgisi konnektori haqiqiy API'ga keltirildi (`public/api` yo'llar, owner-check `results/forbidden/missing` shakli, `private_codes`, base64 doc body, async polling).
✅ TSD pallet skan → optimal joy: `/putaway/scan-suggest` (owner-check→box/unit sanash→Product/Batch→slotting).
✅ World-class slotting: vaznli ko'p-omilli, UI'dan sozlanadigan zona qoidalari (`Zone.putaway_rules`) + dok yaqinligi (xarita koordinatasidan, ABC velocity).
🟡 Smartup konnektori: endpoint ro'yxati va sxemalar tasdiqlangan, lekin koddagi yo'llar (`txs`/`mxsx`) hali to'g'rilanmagan.
🟡 Frontend: skeleton sahifalar bor (Login, Dashboard, Stock, Receipt, Shipment, Settings, 2D/3D).
⬜ Alembic migratsiyalar (hozir faqat DEBUG `create_all`).
⬜ TSD Android ilovasi (offline).
⬜ Testlar, observability, CI/CD.

---

## Phase 0 — Poydevor mustahkamligi (Foundation)
> Maqsad: ishonchli, xavfsiz, kengayuvchan asos.

- ✅ RBAC eager-load tuzatish
- ✅ Konnektor kalitlarini shifrlash (Fernet)
- ✅ Kengaytiriluvchan konnektor registri (yangi ERP/TMS yadroga tegmasdan)
- ⬜ **Alembic boshlang'ich migratsiya** + keyingi har model o'zgarishi migratsiya bilan
- ⬜ Tranzaksiya chegaralari: commit endpoint qatlamida, `get_db` rollback-on-error
- ⬜ Tenant izolyatsiyasi: `require_warehouse_access` dependency + `User.warehouse_scope` ni hamma joyda qo'llash
- ⬜ StockItem parallellik: `SELECT … FOR UPDATE` / atomik UPDATE + `qty>=0` cheklov
- ⬜ AuditLog modeli (kim/qachon/nima — har o'zgarish)
- ⬜ Login rate-limit + brute-force himoyasi
- ⬜ Test karkasi (pytest-asyncio, test DB, fixture'lar) + CI
- ⬜ CORS sozlanadigan origin; `.gitignore`; structured logging + request id

**Bajarildi mezoni:** migratsiyalar bilan toza deploy; oddiy user permission'siz 403, ruxsat bilan ishlaydi; 50 parallel pick over-book qilmaydi; CI yashil.

---

## Phase 1 — Master data + konnektorlar (real)
> Maqsad: Smartup va Asl Belgisi bilan haqiqiy, ishonchli almashinuv.

- ✅ Asl Belgisi: owner-check, private_codes, verify, product-by-gtin, aggregation/disaggregation (base64), doc/codes polling, api-key check/refresh
- ⬜ **Smartup konnektori yo'llari/sxemalari** to'g'rilash: `b/trade/txs/...`, `b/anor/mxsx/...`, `order$export` (`statuses[]`, `begin/end_modified_on`, `order_products[]`, `person_tin`), `balance$export`, `inventory$export`, attach/change-status body shakllari
- ⬜ Master data sync: `mr/inventory$export` → Product (`gtin, box_quant→units_per_box, weight, category` tegi), GTIN↔SKU jadvali
- ⬜ Asl Belgisi `product-registry` bilan boyitish (GTIN bo'yicha)
- ⬜ Konnektor `project_code` trade/anor farqi; per-warehouse `businessPlaceId`/`warehouse_code` mapping
- ⬜ Outbox 2-bosqichli: yuborish + async natija polling (doc/codes status) → WMS holatini yangilash; `next_retry_at`, `SKIP LOCKED`
- ⬜ apiKey 90-kunlik avto-yangilash (scheduler)
- ⬜ Inkremental sync (`modified_on`) rejali job + 7-kun oynasi/limit hisobi
- ⬜ UI: konnektor sozlash formasi (`/connectors/specs` dan), test tugmasi, sync holati

**Bajarildi mezoni:** UI'dan kalit kiritib, Smartup'dan SKU va qoldiq, Asl Belgisi'dan owner-check real keladi; test probe yashil.

---

## Phase 2 — Kirim + Putaway + Slotting (Inbound)
> Maqsad: pallet keldi → skanla → optimal joyga qo'y.

- ✅ TSD pallet skan → owner-check → box/unit sanash → Product/Batch resolve
- ✅ Slotting: vaznli ball, zona qoidalari (UI), dok yaqinligi (koordinata), ABC velocity, og'irlik→yarus, konsolidatsiya, FEFO
- ✅ Receipt: hujjat + ledger + putaway task (resolver bilan)
- ✅ Putaway confirm: operator yacheyka skanlab tasdiqlaydi → `to_location` ledger, StockItem + Location holati + MC location yangilanadi
- ✅ Zavod kirimi: Smartup `mkw/input$export` (`GET /receipt/production-inputs`) — fizik bilan solishtirish uchun
- ✅ MC ierarxiyasini saqlash (pallet→box, parent_code bilan) — recall uchun
- ✅ Karantin/QC moduli (tenant `quarantine_on_receipt`; `/quarantine` release/block)
- ✅ Istisnolar: noma'lum kod, forbiddenCode, noto'g'ri yacheyka, product_not_mapped → `/exceptions` (eskalatsiya, assign, resolve)

**Bajarildi mezoni:** real pallet skan → 1 soniyada to'g'ri zonadagi (19L/0.5L) eng yaqin dok joyi taklif bo'ladi; tasdiqdan keyin qoldiq va xarita yangilanadi.

---

## Phase 3 — Saqlash, zaxira, xarita (Storage)
- ✅ 2D xarita muharriri (Konva): zona/dok/yacheyka koordinatalari draggable + saqlash (`WarehouseMap.tsx`) — slotting/dok masofasi shundan
- ✅ Zona qoidalari muharriri (UI) + slotting vaznlari sozlash (`/slotting/zones/{id}/rules`, `/slotting/weights`)
- ✅ Yacheyka/qoldiq real-time (SSE: `/realtime/stream` + ledger publish event bus)
- ✅ Qoldiq ko'rinishlari: batafsil join (SKU/partiya/muddat/yacheyka), pagination (`/stock/detailed`, `/stock/summary`, `StockView.tsx`)
- ✅ Ochiq/yopiq pallet holati kuzatuvi (detailed view + summary)
- ✅ Label-service: yacheyka (Code128) + pallet (SSCC) ZPL (`/labels/*`, `Labels.tsx`)
- 🟡 3D ko'rish: koordinatadan pseudo-3D (CSS/SVG) bor; to'liq Three.js keyinroq (paket o'rnatilishi kerak)

**Bajarildi mezoni:** admin xaritani UI'da chizadi/o'zgartiradi, slotting o'sha koordinatalardan dok masofasini hisoblaydi.

---

## Phase 4 — Terish + Otgruzka (Outbound) ✅
- ✅ Pick plan (FEFO/FIFO), marshrut optimizatsiyasi (route_optimizer)
- ✅ Smartup `order$export` (B#W) → `/shipment/orders` → terish vazifasi; validatsiya (GTIN→SKU, over-pick rad etish)
- ✅ Qisman pallet: to'liq box'lar, dezagregatsiya outbox (`doc/transport-code-disaggregation`), ochiq-pallet qoidasi
- ✅ Kod biriktirish: `order$import_order_marking_codes` + `order$change_status` (outbox, B#S)
- ✅ Booking → shipment ledger; TSD scan validatsiya (`/shipment/scan`)
- 🟡 Staging/dok bandligi (asosiy bor; vizualizatsiya Phase 7)

**Bajarildi mezoni:** zakaz → terish → kodlar Smartup'ga biriktiriladi, status o'zgaradi; qisman pallet dezagregatsiya bo'ladi.

---

## Phase 5 — Qolgan hujjatlar + Svereka (Reconciliation) ✅
- ✅ Ichki ko'chirish/replenishment (rezerv→pick) + Smartup `mkw/movement` outbox
- ✅ Inventarizatsiya (full + cycle count) → diff ledger + `mkw/stocktaking$import` (`balance_quantity`)
- ✅ Spisaniye → `mkw/writeoff$import`; Vozvrat → RETURN_IN + disposition
- ✅ **Svereka engine** (`run_reconciliation`): WMS Ledger ↔ Smartup `balance$export` (+Asl Belgisi); farqlar hisoboti
- ✅ Eksport: CSV (stock, svereka) — Excel/PDF opsional (paket bo'lsa)

**Bajarildi mezoni:** svereka farqlar hisobotini beradi; hujjatlar idempotent (`external_id`).

---

## Phase 6 — TSD Android (offline-first) ✅
- ✅ Native Android ilova (mavjud PM84 skaner loyihasi davom ettirildi) — WMS backend bilan
- ✅ Offline navbat (`OfflineQueue`) + `SyncManager` (replay, 401→re-login, backoff/drop) + `ConnectivityHelper`
- ✅ Tez skanlash: PM84 hardware skaner (DecodeBroadcastReceiver) — DataMatrix/Code128; `ScanBaseActivity` umumiy baza
- ✅ Ekranlar: **Kirim** (ReceiptActivity→/receipt), **Putaway** (scan-suggest+offline confirm), **Terish/Otgruzka** (PickingActivity: orders→pick-task→confirm), **Inventarizatsiya** (InventoryActivity: GTIN→count), **Yorliqlar** (LabelActivity: ZPL→share/print)
- ✅ Vazifa boshqaruvi: `TasksActivity` (ro'yxat + sync holati); barcha yozuv operatsiyalari offline-aware (`WmsOps`)
- 🟡 Faqat on-device Gradle build/QA qoldi (Android Studio, JDK 17 — bu yerda JDK 8 bois build qilib bo'lmadi)

**Bajarildi:** to'liq operator oqimlari (kirim/putaway/terish/inventar/yorliq/tasklar) + offline navbat + sync. Statik tekshiruv (XML/Kotlin) toza; build — Android Studio'da.

---

## Phase 7 — Analitika + Optimizatsiya ✅
- ✅ KPI (`/analytics/kpi`) + throughput (`/analytics/throughput` kunlik kirim/chiqim grafigi)
- ✅ Yacheyka tarixi Ledger'dan (`/analytics/location-history`)
- ✅ ABC-tahlil + re-slotting tavsiyasi (`/analytics/abc-suggestions`)
- ✅ Heatmap (`/analytics/heatmap`) — aylanish intensivligi
- ✅ Muddat/bloklangan/ochiq-pallet dashboard (`/analytics/dashboard` + Analytics UI kartalari + expiry-alerts)
- ✅ Real-time monitoring (SSE `/realtime/stream` + 30s refresh dashboard)
- ✅ 3D digital twin: lazy-loaded WebGL (three.js, alohida chunk — faqat ochilganda), InstancedMesh (1 draw call) + render-on-demand (qotmaydi); `/analytics/occupancy` agregat rang bilan. Pseudo-3D (CSS) ham default sifatida qoladi.

---

## Phase 8 — Productizatsiya (SaaS, world-class) ✅
- ✅ Multi-tenant onboarding: `POST /tenants/provision` (tenant+admin+sklad), tenant update, settings get/patch (maket/UOM/til/ish oqimi)
- ✅ Plagin konnektorlar: 1C / SAP / TMS registrda (stub) — yadroga tegmasdan, UI'da avtomatik (`/connectors/specs`)
- ✅ i18n (ru/uz/en): `LanguageProvider` + `useI18n`/`t()` + til almashtirgich (Settings); ru ustuvor
- ✅ Billing/tariff + SLA: `/billing/plans`, `/billing/usage` (limit vs foydalanish), `POST /tenants/{id}/plan`, `/billing/sla`
- ✅ Rollarni kengaytirish: RBAC seed katalogi (billing qo'shildi) + tizim rollari

**Bajarildi:** SaaS onboarding + kengaytiriluvchan konnektorlar + i18n + billing/SLA.

---

## Cross-cutting (doimiy)
- Xavfsizlik: TLS, secret store, 2FA (ixtiyoriy), audit, tenant izolyatsiya
- Observability: structured log, metrics, integratsiya holati, alert
- Sifat: unit+integration testlar, contract test (Smartup/Asl Belgisi mock), CI/CD
- Hujjatlashtirish: API (OpenAPI), runbook, ERD

---

## Tavsiya etilgan ketma-ketlik (milestones)
1. **M1 (poydevor+real integratsiya):** Phase 0 + Phase 1 → UI'dan kalit, real master data + owner-check.
2. **M2 (inbound demo):** Phase 2 + Phase 3 (2D xarita) → real pallet skan → optimal joy → tasdiq → xarita.
3. **M3 (outbound):** Phase 4 → zakaz → terish → Smartup biriktirish.
4. **M4 (to'liq operatsion):** Phase 5 + Phase 6 → svereka + TSD offline.
5. **M5 (world-class):** Phase 7 + Phase 8 → analitika, 3D, SaaS productization.
