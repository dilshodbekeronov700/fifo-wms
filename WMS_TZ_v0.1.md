# Texnik topshiriq (TZ) — Tayyor mahsulot skladini avtomatlashtirish (WMS)

**Versiya:** 0.1 (qoralama)
**Sana:** 2026-06-10
**Mahsulot turi:** Sklad boshqaruvi tizimi (WMS) — bulutli SaaS
**Birinchi mijoz:** Ichimlik suvi ishlab chiqarish zavodi
**Maqsad:** Smartup'dan funksionalroq, boshqa skladlarga ham sotiladigan mustaqil WMS platformasi

> Bu hujjat — birinchi to'liq qoralama. "TBD" / "Tasdiqlash kerak" deb belgilangan joylar mijoz/ishlab chiqarish bilan aniqlanadi.

---

## 1. Hujjat haqida

### 1.1 Maqsad
Hujjat suv zavodining tayyor mahsulot skladini avtomatlashtiruvchi WMS tizimiga qo'yiladigan funksional va nofunksional talablarni belgilaydi. Tizim Smartup ERP va Asl Belgisi (xtrace) markirovka tizimi bilan integratsiyalashadi, sklad operatorlari uchun Android TSD ilovasini, ofis foydalanuvchilari uchun web-ilovani taqdim etadi.

### 1.2 Auditoriya
Mahsulot egasi, ishlab chiqarish direktori, sklad rahbari, dasturchilar jamoasi (backend, frontend, mobil), integratsiya muhandislari, QA, DevOps.

### 1.3 Terminlar va qisqartmalar

| Termin | Izoh |
|---|---|
| WMS | Warehouse Management System — sklad boshqaruvi tizimi |
| TSD | Terminal sbora dannyx — qo'lda ushlanadigan Android skaner |
| SKU | Stock Keeping Unit — alohida tovar artikuli |
| DataMatrix / MC | Marking Code — Asl Belgisi markirovka kodi (har shishada unique) |
| KIZ | Identifikatsiya kodi (MC ning bir qismi) |
| GTIN | Global Trade Item Number |
| SSCC | Transport (pallet) qadoq seriyali kodi |
| GROUP | Guruh qadoq (latok/blok) — box darajasi |
| BOX_LV_1/2 | Transport qadoq (pallet) darajalari |
| FEFO / FIFO | First Expired/First In, First Out |
| ABC | Aylanish tezligi bo'yicha SKU tasnifi |
| Ledger | O'zgarmas harakatlar jurnali (event-sourced) |
| Tenant | SaaS ijarachi (alohida mijoz/tashkilot) |
| BP (businessPlaceId) | Asl Belgisi'dagi biznes joy identifikatori |
| SCP | Supply Chain Participant (Asl Belgisi terminologiyasi) |
| EDS | Elektron raqamli imzo |
| RBAC | Role-Based Access Control |

---

## 2. Loyiha umumiy tavsifi

### 2.1 Biznes konteksti
Zavodda suv liniyada quyiladi, har shishaga unique DataMatrix kod bosiladi, muomalaga kiritish (utilizatsiya) liniyada amalga oshiriladi. Tayyor mahsulot pallet ko'rinishida tayyor mahsulot skladiga keladi. Sklad zavod hududida, buxgalteriya/moliya va boshqa bo'limlar ofisda — zavoddan 10+ km uzoqda joylashgan.

Hozirgi holatda hisob Smartup ERP'da yuritiladi, lekin Smartup haqiqat manbasi sifatida ishonchli emas (super-admin istalgan ma'lumotni o'zgartirishi mumkin). WMS o'z fizik haqiqat manbasini (ledger) yuritadi va Smartup bilan svereka qiladi; keyinchalik to'liq haqiqat manbasiga aylanish imkoniyatini saqlaydi.

### 2.2 Asosiy printsiplar (productizatsiya uchun majburiy)
1. **Yadro ERP'dan mustaqil.** Smartup va Asl Belgisi — almashtiriladigan konnektorlar; boshqa mijozda boshqa ERP/marker bo'lishi mumkin.
2. **Ko'p-ijarachilik (multi-tenant)** — sxema darajasidan boshlab izolyatsiya.
3. **Ko'p-skladlilik** — bitta tenant ostida bir nechta sklad/filial.
4. **Sozlanuvchanlik** — sklad maketi, o'lchov birliklari, ish oqimlari, saralash strategiyalari, karantin moduli — yoqiladigan/sozlanadigan.
5. **API-first** — web va TSD bitta backend API'ni iste'mol qiladi.
6. **O'zgarmas audit (event-sourced ledger)** — har harakat kim/qachon/nima/sababi bilan yoziladi.
7. **Lokalizatsiya** — ru ustuvor, uz; keyinchalik boshqa tillar.

### 2.3 Miqyos ko'rsatkichlari (birinchi mijoz)
- ~600 pallet-mesto, 4 qator
- Yuklash nuqtalari: 3 ta; odam kirish eshigi: 1 ta; xom-ashyo darvozasi: 1 ta; ishlab chiqarish darvozasi: 1 ta
- SKU: jami 64, asosiy 6–15 (mavsumga qarab)
- Foydalanuvchilar: boshlang'ich ~50, kelajakda o'sishi mumkin
- Kunlik aylanma (kirim/chiqim pallet/box): TBD — DB o'lchamlash uchun kerak

---

## 3. Ko'lam (Scope)

### 3.1 Kiradi
Kirim, yo'naltirilgan joylashtirish (slotting), saqlash va yacheyka boshqaruvi, zaxira hisobi (kod ierarxiyasi bilan), terish va otgruzka, ichki ko'chirish/replenishment, vozvrat, inventarizatsiya, spisaniye; 2D tahrirlanadigan + 3D ko'rish xaritasi; analitika; RBAC; Smartup va Asl Belgisi integratsiyasi; Android TSD (offline); label chop etish; vazifa boshqaruvi.

### 3.2 Kirmaydi (hozircha)
Ishlab chiqarish liniyasini boshqarish (MES), kod chiqarish (ICOM buyurtma — liniya), utilizatsiya/muomalaga kiritish (liniya), buxgalteriya/moliya hisobi (Smartup), transport/logistika marshrutizatsiyasi (faqat dok darajasida), e-faktura yaratish (Smartup).

### 3.3 Kelajak bosqichlari uchun (opsional modullar)
Qaytariladigan tara (19L oborotnaya) kuzatuvi, karantin/QC kutish moduli, ko'p-til kengaytmasi, ishlab chiqarishdan kirimni WMS posting qilishi.

---

## 4. Aktyorlar va rol modeli (RBAC)

### 4.1 Aktyorlar
- **Sklad operatori (TSD):** kirim, joylashtirish, terish, ichki ko'chirish, inventarizatsiya — asosan TSD orqali.
- **Smena boshlig'i / sklad rahbari:** vazifalarni taqsimlash, monitoring, istisnolarni hal qilish, xaritani ko'rish/tahrirlash.
- **Ofis foydalanuvchisi (buxgalteriya/moliya):** asosan ko'rish — qoldiqlar, hujjatlar, analitika, svereka.
- **Tenant-admin:** sklad maketi, foydalanuvchilar, rollar, sozlamalar, konnektor kalitlari.
- **Super-admin (platforma):** tenantlar boshqaruvi (faqat platforma egasi).
- **Integratsiya (tizim):** Smartup va Asl Belgisi bilan avtomatik almashinuv.

### 4.2 RBAC printsiplari
- Ruxsatlar matritsasi: rol → resurs → amal (ko'rish/yaratish/o'zgartirish/tasdiqlash/o'chirish).
- **Ma'lumot doirasi (data scope):** har user faqat o'z doirasini ko'radi (masalan operator faqat o'z skladi/zonasi/vazifalari; ofis faqat ko'rish). Doiralar: tenant → sklad → zona → operatsiya turi.
- Audit: har bir kirish va o'zgartirish jurnalga yoziladi.
- Rollar sozlanadi (mijozga moslab kengaytiriladi).

---

## 5. Tizim arxitekturasi (yuqori daraja)

### 5.1 Komponentlar
- **Backend (API-first):** REST + jonli yangilanish (WebSocket/SSE — xarita va vazifalar uchun). Domen mantig'i ERP'dan mustaqil.
- **Inventory Ledger:** o'zgarmas harakatlar jurnali; qoldiqlar undan hisoblanadi (derived). Haqiqat manbasi shu.
- **Web-ilova:** ofis + sklad rahbari (desktop). 2D/3D xarita, analitika, hujjatlar, sozlamalar.
- **Android TSD ilovasi:** offline navbat bilan; skanlash, vazifalar, agregatsiya/dezagregatsiya.
- **Konnektor qatlami (anti-corruption layer):** Smartup-connector, AslBelgisi-connector; outbox + retry + idempotentlik.
- **Reconciliation engine:** WMS ↔ Smartup balans/hujjat svereka.
- **Label-service:** yacheyka va pallet (SSCC) yorliqlari (Zebra/printer integratsiyasi).
- **Auth/RBAC service:** identifikatsiya, tokenlar, rollar, audit.

### 5.2 Multi-tenant
Tenant izolyatsiyasi sxema yoki qator darajasida (tanlash arxitektura qaroriga qoldiriladi — TBD); har so'rovda tenant konteksti majburiy; tenant-aro ma'lumot oqishi taqiqlanadi.

### 5.3 Joylashuv
Bulutli SaaS (markaziy). Zavodda internet barqarorligi cheklangan bo'lishi mumkin → TSD offline rejimi kritik (5.1, 8-bo'lim).

---

## 6. Ma'lumotlar modeli (asosiy entitilar)

> Quyida mantiqiy model. Aniq sxema (jadval/ustun, indekslar) loyihalash bosqichida ERD bilan rasmiylashtiriladi.

| Entiti | Asosiy maydonlar (qisqacha) |
|---|---|
| **Tenant** | id, nom, sozlamalar, til, valyuta |
| **Warehouse (sklad)** | id, tenant_id, nom, manzil, smartup_warehouse_code |
| **Zone (zona)** | id, warehouse_id, tur (rezerv/pick/ochiq-pallet/staging/dok/karantin/vozvrat), koordinatalar |
| **Location (yacheyka)** | id, zone_id, kod (masalan A-01-03-02), tur, koordinata+yarus, sig'im, og'irlik cheklovi, barkod (Code128/QR) |
| **Product (SKU)** | id, tenant_id, smartup_product_code, gtin, nom (i18n), o'lchov birligi, box ichidagi unit soni, pallet ichidagi box soni, ABC sinfi, og'irlik/hajm |
| **Batch (partiya)** | id, product_id, partiya raqami, ishlab chiqarilgan sana, muddat, status (bloklangan/available — opsional karantin) |
| **MarkingCode (kod)** | id, code (to'liq MC), gtin, packageType (UNIT/GROUP/BOX_LV_1/2), parent_code, status (Asl Belgisi: RECEIVED/APPLIED/INTRODUCED/WITHDRAWN/WRITTEN_OFF), product_id, batch_id, location_id |
| **CodeHierarchy** | parent_code → child_code (agregatsiya daraxti) |
| **StockItem (qoldiq)** | warehouse_id, location_id, product_id, batch_id, miqdor, holat (available/booked/blocked), pallet holati (ochiq/yopiq) |
| **Document (hujjat)** | id, tur (kirim/otgruzka/ko'chirish/inventar/spisaniye/vozvrat), status, external_id, smartup_id, foydalanuvchi, sana |
| **Task (vazifa)** | id, tur (putaway/pick/replenish/count), holat, biriktirilgan operator, manba hujjat, qadamlar |
| **LedgerEntry** | id, vaqt, user, harakat turi, manba/maqsad yacheyka, product/batch/code, miqdor, sabab, hujjat havolasi (o'zgarmas) |
| **User / Role / Permission** | RBAC entitilari, data scope |
| **AuditLog** | kim, qachon, qaysi resurs, qanday amal, eski/yangi qiymat |
| **OutboxMessage** | konnektor, payload, holat, urinishlar soni (integratsiya ishonchliligi) |

---

## 7. Funksional talablar (modullar)

### 7.1 Master data (ma'lumotnomalar)
- SKU/nomenklatura, o'lchov birligi, box/pallet ichidagi miqdor — Smartup References (`Inventory$export`) dan + GTIN bo'yicha Asl Belgisi `product-registry` dan boyitiladi.
- GTIN ↔ SKU (smartup product_code) moslashtirish jadvali — otgruzka validatsiyasi uchun kritik.
- Sklad maketi (zonalar, yacheykalar, kodlar) tenant-admin tomonidan kiritiladi/tahrirlanadi (2D muharrir, 9-bo'lim).

### 7.2 Kirim (prixod) — liniyadan tayyor mahsulot
1. Pallet skladga keladi; TSD transport kodni (SSCC/BOX_LV) skanlaydi.
2. WMS Asl Belgisi `cod/nested-codes/owner-check` (bizning TIN bilan) chaqiradi → ichidagi box/unit'lar, egalik tasdig'i, miqdorlar olinadi.
3. Kerak bo'lsa `cod/private/codes` bilan partiya/muddat/status boyitiladi.
4. Tizim partiya, muddatni biriktiradi; (opsional) karantin holatini qo'yadi.
5. Putaway vazifasi yaratiladi (7.3).
6. Ledger'ga "kirim" yozuvi; Smartup tomoni — **TBD** (3.3, 16-bo'lim): balansdan o'qish + fizik solishtirish; agar WMS posting qilishi kerak bo'lsa — mos hujjat.

### 7.3 Joylashtirish (Putaway) va slotting
- **Yo'naltirilgan joylashtirish:** tizim qayerga qo'yishni taklif qiladi. Algoritm omillari: bo'sh sig'im, yuklash nuqtasigacha masofa, SKU ABC-tezligi, bir SKU/partiyani jamlash, FEFO bo'yicha guruhlash, og'irlik (og'ir tovar pastki yarusga), yacheyka turi.
- **ABC-slotting:** SKU lar aylanish tezligiga qarab A/B/C ga ajratiladi; A — yuklash nuqtalariga yaqin zonaga. Mavsumiylik tufayli davriy **re-slotting** tavsiyasi.
- Operator taklif qilingan yacheykaga qo'yadi va yacheyka kodini skanlab tasdiqlaydi.
- Ledger'ga joylashtirish yozuvi; xaritada yangilanadi.

### 7.4 Saqlash va yacheyka boshqaruvi
- Yacheyka holati: bo'sh / band / qisman / bloklangan.
- Yacheyka kodlash sxemasi: `Qator-Stellaj-Yarus-Pozitsiya` (masalan `A-01-03-02`), katta o'qiladigan matn, **mahsulot DataMatrix'idan farqli simvologiya** (yacheyka = Code128 yoki QR — chalkashlikni oldini olish).
- Bir yacheykada bir nechta SKU/partiya bo'lishi konfiguratsiyaga bog'liq (odatda zona qoidasi bilan cheklanadi).

### 7.5 Zaxira va kod ierarxiyasi
- Qoldiq SKU/partiya/muddat/yacheyka/kod kesimida.
- Agregatsiya ierarxiyasi: pallet (BOX_LV) → box (GROUP) → unit (UNIT). Terish minimal **box (GROUP)** darajasida — unit faqat kuzatuvda (bittalab shishaga buzilmaydi).
- **Ochiq/yopiq pallet** holati: qisman terish boshlangan pallet "ochiq" bo'ladi.
- Holatlar: available / booked (zakazga bron) / blocked (karantin/muddat).
- Barcha o'zgarishlar Ledger orqali (o'zgarmas).

### 7.6 Terish (Picking) va otgruzka
**Asosiy oqim (tasdiqlangan):**
1. Smartup'da zakaz (Order) yaratiladi.
2. WMS `order$export` bilan zakazni o'qiydi (masalan "shipga kutilmoqda" statusidagi).
3. Tizim terish vazifasini yaratadi, marshrutni optimallashtiradi (4 qator, 3 yuklash nuqtasi).
4. Operator TSD bilan teradi; har skanlangan kodni Asl Belgisi orqali aniqlab (GTIN→SKU), **zakaz pozitsiyasiga moslikni tekshiradi**: mos kelsa qabul, mos kelmasa yoki miqdor oshsa **rad** etiladi.
5. **Qisman pallet (masalan 80 dan 68):** to'liq box'lar olinadi; pallet/box buzilsa TSD'dan Asl Belgisi'ga **dezagregatsiya** (`doc/transport-code-disaggregation`) yuboriladi; qolgan box'lar "ochiq-pallet/qoldiq" yacheykaga ko'chiriladi. Qoida: bir SKU bo'yicha bir vaqtda **bitta ochiq pallet** (avval ochilgandan olinadi).
6. Terish tugagach WMS kodlarni Smartup zakaziga `order$import_order_marking_codes` (deal_id + product_unit_id + marking_codes[]) bilan biriktiradi va `order$status_change` bilan statusni o'zgartiradi.
7. Smartup faktura chiqaradi → Asl Belgisi'da `OWNER_CHANGE` avtomatik (WMS to'g'ridan tegmaydi).
8. Ledger'ga otgruzka/booking yozuvlari.

### 7.7 Ichki ko'chirish va replenishment
- Yacheykadan yacheykaga / zonadan zonaga ko'chirish (TSD bilan skanlash).
- Replenishment: rezerv → pick-zona to'ldirish (avtomatik taklif).
- Smartup `mkw/movement$import` (bir tashkilot ichida) yoki `mfm/movement` (boshqa yuridik shaxsga, masalan zavod↔ofis — agar alohida yuridik shaxs bo'lsa).

### 7.8 Vozvrat
- Mijoz vozvrati: Smartup `mdeal/return$export` dan o'qiladi; tovar qayta qabul qilinadi; kod qayta tekshiriladi (`verify`/`private codes`); disposition: qayta saqlash / karantin / spisaniye.
- Postavshikka qaytarish: `mkw/return$import|$export`.

### 7.9 Inventarizatsiya
- To'liq va tanlama (cycle count) — TSD orqali skanlash.
- Farqlar hisoboti; Smartup `mkw/stocktaking$import` orqali yuboriladi (balance_quantity bilan).

### 7.10 Spisaniye (Write-off)
- Shikast, muddat o'tishi va h.k.; Smartup `mkw/writeoff$import` (marking_codes bilan). Eslatma: status "C - Completed" API'da emas — yakunlash Smartup'da mas'ul shaxs tomonidan.
- Asl Belgisi tomonida kerak bo'lsa tegishli hisobot (withdrawalReason bilan) — **TBD**.

### 7.11 Vazifa boshqaruvi (TSD)
- Operatorlarga vazifa taqsimlash (putaway/pick/replenish/count), prioritet, holat kuzatuvi, smena boshlig'i monitoringi.

### 7.12 Label chop etish
- Yacheyka yorliqlari (kod + o'qiladigan matn) va pallet/SSCC yorliqlari; printer integratsiyasi (masalan ZPL/Zebra). Joyida (TSD/mobil printer) chop etish.

### 7.13 Istisnolar (exceptions)
- Tizimda yo'q kod, egalik mos emas (forbiddenCode), noto'g'ri yacheyka, shikastlangan tovar, zakazga mos kelmaydigan skanlash — har biri uchun ish oqimi va smena boshlig'iga eskalatsiya.

---

## 8. TSD ilovasi (Android, offline)
- Alohida Android ilova; web bilan bitta backend API.
- **Offline rejim:** aloqa uzilganda lokal navbat (operatsiyalar saqlanadi), tiklanganda sinxron; konflikt yechimi (last-write + Ledger asosida tekshiruv).
- Tez skanlash (DataMatrix mahsulot, Code128/QR yacheyka).
- Funksiyalar: kirim, putaway, picking, ko'chirish, inventar, agregatsiya/dezagregatsiya hisoboti (Asl Belgisi'ga TSD'dan), label chop etish.
- Mavjud TSD ilovasi bilan munosabat: **o'zimizniki quriladi** (SaaS uchun); eski ilovani to'liq almashtirish/birga yashash — **TBD**.

---

## 9. 2D/3D xarita va vizualizatsiya
- **2D tahrirlanadigan xarita:** tenant-admin qatorlar, stellajlar, yuklash nuqtalari (3), darvozalar (xom-ashyo, ishlab chiqarish), odam eshigi, zonalarni joylab, yacheyka kodlarini biriktiradi (web canvas: Konva.js yoki SVG).
- **Layout abstrakt saqlanadi** (koordinata + o'lcham + yarus) — 2D va 3D bir xil ma'lumotdan render bo'ladi.
- **3D ko'rish vizualizatsiyasi:** keyingi bosqich, faqat-ko'rish (Three.js). Tahrirlash 2D'da qoladi.
- Real vaqt: yacheyka bandligi, qoldiq, qaysi mahsulot qayerda.
- **Issiqlik-xarita (heatmap):** aylanish intensivligi; qulay joylashtirish tavsiyasi.

---

## 10. Analitika va hisobotlar
- Yacheyka tarixi: "bu joydan qachon qaysi mahsulot olingan" (Ledger'dan).
- ABC-tahlil, aylanish tendensiyasi, re-slotting tavsiyasi.
- Dwell time, dok bandligi, throughput, buyurtma bajarilishi (fulfillment) KPI lari.
- Muddat yaqinlashgan partiyalar, bloklangan zaxira, ochiq palletlar.
- Svereka hisobotlari (WMS ↔ Smartup farqlari).
- Eksport: Excel/CSV/PDF.

---

## 11. Integratsiya

### 11.1 Umumiy printsiplar
- **Konnektor qatlami (anti-corruption layer):** har ERP/marker uchun alohida adapter; yadro standart ichki modelda ishlaydi.
- **Idempotentlik:** har WMS hujjatiga `external_id` qo'yiladi (Smartup bunga tayanadi).
- **Outbox + retry:** tashqi chaqiruvlar navbatga yoziladi, uzilishda yo'qolmaydi, qayta uriniladi.
- **Asinxron status:** Asl Belgisi hisobotlari async — `doc/storage/docs/{id}` va `.../docs/{id}/codes` orqali SUCCESS/WARNING/ERROR pollinglanadi.
- **Reconciliation:** rejali svereka — Smartup `Inventory Balance$export` va Asl Belgisi `cod/exports` bilan WMS Ledger qoldig'i solishtiriladi; farqlar ish oqimiga chiqadi.
- **"Egalik" bayrog'i:** boshida Smartup rasmiy hisob, WMS fizik haqiqat; keyinchalik WMS SoT ga o'tishi uchun yadroga tegmasdan qayta sozlash.

### 11.2 Smartup (ERP) — `b/anor/...`, `b/trade/...`
- **Auth:** Basic Auth (login/parol, base64, HTTPS); header'lar `project_code`, `filial_id`. **Aniq base URL / project_code / filial_id — TBD** (namuna: `smartup.online`, `anor`/`trade`).
- **Cheklovlar:** kunlik limit (References 100, kam ishlatiladigan 300, tez-tez 500); export oynasi ~7 kun (ba'zi hujjatlarda `modified_on` 30 kun); import ≤5000 obyekt/so'rov. → **Inkremental sinxron (`modified_on`) + Ledger asosiy.**

| WMS operatsiyasi | Endpoint | Yo'nalish |
|---|---|---|
| Kirim (prixod) | `mkw/input$import` · `$export` (xaridga bog'liq) | TBD (ishlab chiqarish kirimi aniqlanishi kerak) |
| Otgruzka | `tdeal/order$export`, `tdeal/order$import_order_marking_codes`, `tdeal/order$change_status` | Smartup→WMS→Smartup |
| Ichki ko'chirish | `mkw/movement$import` · `$export` | WMS↔Smartup |
| Tashkilotlararo ko'chirish | `mfm/movement$import` · `$export` · `$change_status` | WMS↔Smartup |
| Mijoz vozvrati | `mdeal/return$export` | Smartup→WMS |
| Postavshikka qaytarish | `mkw/return$import` · `$export` | WMS↔Smartup |
| Inventarizatsiya | `mkw/stocktaking$import` · `$export` | WMS→Smartup |
| Spisaniye | `mkw/writeoff$import` | WMS→Smartup |
| Qoldiq (svereka) | `Others → Inventory Balance$export` | Smartup→WMS |
| Master data | `References → Inventory`, `Price type`, `Producers`, `Legal/Natural persons`, `Workspaces`, `Contract` | Smartup→WMS |

### 11.3 Asl Belgisi (xtrace) — `https://xtrace.aslbelgisi.uz`
- **Auth:** Business user **apiKey** (Bearer, 90 kun, avtomatik yangilash kerak — `party/parties/{tin}/api-keys/refresh`). Technical user (login/parol→token) faqat ICOM/kod buyurtma uchun — **liniya zimmasida** (WMS'ga ehtimol kerak emas).
- **Mahsulot guruhi:** `water`.
- **Imzo/format:** agregatsiya/dezagregatsiya hujjatlari base64 JSON (ba'zilarida xossalar A–Z tartibida); EDS imzo maydoni bor (suv uchun majburiy emas, siyosatga qarab — **TBD**).
- **Cheklovlar:** owner-check ≤10 so'rov/sek, ≤100 kod/so'rov; hisobotlar 100/daqiqa; agregatsiya sig'imi GROUP=200, BOX_LV_1=1500, BOX_LV_2=500; bitta hisobotda ≤30000 kod.

| WMS funksiyasi | Endpoint | Tur |
|---|---|---|
| Transport kod ichini olish + egalik | `cod/nested-codes/owner-check` | O'qish |
| Batafsil kod ma'lumoti | `cod/private/codes` | O'qish |
| Kod haqiqiyligi | `code-verification/verify` | O'qish |
| Egalikdagi kodlar ro'yxati (svereka) | `cod/exports` (+`/status`, `/result`) | O'qish |
| SKU master (GTIN bo'yicha) | `product-registry/product`, `/product/id` | O'qish |
| Agregatsiya (qayta yig'ish) | `doc/aggregation` | Yozish (TSD) |
| Dezagregatsiya (pallet buzish) | `doc/transport-code-disaggregation` | Yozish (TSD) |
| Hujjat holati | `doc/storage/docs/{id}`, `/docs/{id}/codes` | O'qish |
| Kontragent statusi | `party/parties/{tin}/status` | O'qish |

> Eslatma: muomalaga kiritish/utilizatsiya (liniya) va otgruzkadagi `OWNER_CHANGE` (Smartup faktura orqali) WMS ko'lamiga **kirmaydi**.

---

## 12. Saralash strategiyalari
- **FEFO** (asosiy) — yaroqlilik muddati bo'yicha.
- **FIFO** (ikkilamchi) — ishlab chiqarilgan sana bo'yicha (muddatlar teng bo'lsa).
- **Partiya (lot)** bo'yicha kuzatuv — recall/qaytarib olish uchun majburiy (har KIZ → partiya → qaysi dok/mijoz).
- **Karantin/QC kutish** — sozlanadigan modul (bloklangan→available); birinchi mijozda mahsulot allaqachon tekshiruvdan o'tib keladi, lekin moduл platformaga qo'shiladi.
- LIFO — qo'llanilmaydi.

---

## 13. Nofunksional talablar (NFR)

### 13.1 Xavfsizlik
- Parollar argon2/bcrypt bilan hash; HTTPS/TLS majburiy.
- Sessiya: JWT + refresh; ixtiyoriy 2FA.
- Login urinishlariga rate-limit; brute-force himoyasi.
- RBAC + ma'lumot doirasi (har user faqat o'z doirasini ko'radi).
- Tenant izolyatsiyasi; tenant-aro oqish taqiqlanadi.
- Tashqi tizim kalitlari (Smartup Basic, Asl Belgisi apiKey) shifrlangan saqlanadi (secret store); apiKey muddatigacha avtomatik yangilanadi.
- O'zgarmas audit jurnali (kim/qachon/nima).

### 13.2 Ishlash (performance)
- Skanlashga javob real vaqtda (TSD UX uchun maqsadli kechikish belgilanadi — TBD).
- ~50 bir vaqtdagi foydalanuvchi, o'sishga moslashuvchan.

### 13.3 Ishonchlilik
- Offline TSD; outbox/retry; tashqi tizim uzilishida ma'lumot yo'qolmasligi.
- Idempotent operatsiyalar (`external_id`).

### 13.4 Masshtablanish
- Multi-tenant, ko'p-sklad; gorizontal kengayishga tayyor arxitektura.

### 13.5 Lokalizatsiya
- ru (ustuvor), uz; til qo'shish kengaytiriladigan (i18n resurslari).

### 13.6 Kuzatuvchanlik
- Loglar, metrikalar, integratsiya holati monitoringi, ogohlantirishlar.

---

## 14. Productizatsiya (SaaS)
- Har mijoz — alohida tenant; sozlamalar tenant darajasida.
- Sozlanadigan: sklad maketi, o'lchov birliklari, ish oqimlari, saralash strategiyalari, karantin, til, konnektorlar (Smartup/boshqa ERP), markirovka (Asl Belgisi/yo'q).
- Konnektorlar plagin sifatida — yangi ERP qo'shish yadroga tegmasdan.

---

## 15. Rivojlanish bosqichlari (yo'l xaritasi)
> MVP emas — har bosqich chuqur o'ylangan, lekin yetkazib berish bosqichli.

- **B1 — Yadro va master data:** Ledger, tenant/sklad/yacheyka/SKU modeli, 2D xarita muharriri, RBAC, auth.
- **B2 — Kirim + putaway + zaxira:** TSD kirim, owner-check integratsiyasi, slotting, qoldiq, yacheyka boshqaruvi.
- **B3 — Terish + otgruzka:** Smartup zakaz oqimi, validatsiya, qisman pallet, dezagregatsiya, kod biriktirish.
- **B4 — Svereka + qolgan hujjatlar:** Inventory Balance svereka, ko'chirish, vozvrat, inventar, spisaniye.
- **B5 — Analitika + 3D + optimizatsiya:** heatmap, ABC/re-slotting, KPI, 3D ko'rish.

---

## 16. Taxminlar va ochiq savollar (tasdiqlash kerak)
1. **Tayyor suv Smartup'ga qaysi hujjat orqali kirim qilinadi** (ishlab chiqarish moduli ichkarida posting qiladimi)? Taxmin: balansdan o'qib, fizik qabulni TSD bilan solishtiramiz.
2. Smartup haqiqiy **base URL / `project_code` / `filial_id`**.
3. Zavod va ofis **bir xil yuridik shaxsmi** (ichki ko'chirish `mkw`) yoki boshqami (`mfm`)?
4. Asl Belgisi agregatsiya/dezagregatsiyaga **EDS imzo** majburiymi?
5. Mavjud TSD ilovasini **to'liq almashtiramizmi** yoki birga yashashi kerakmi?
6. Qaytariladigan tara (19L) ko'lamga kiradimi?
7. Kunlik aylanma (pallet/box kirim-chiqim) — DB o'lchamlash uchun.
8. Skanlash javobiga maqsadli kechikish (SLA) qiymatlari.

---

## 17. Ilovalar

### 17.1 Markirovka kodi statuslari (Asl Belgisi)
`RECEIVED` → `APPLIED` → `INTRODUCED` → (`WITHDRAWN` / `WRITTEN_OFF`)

### 17.2 Qadoq turlari
`UNIT` (shisha) → `GROUP` (latok/box) → `BOX_LV_1`/`BOX_LV_2` (pallet/transport, SSCC)

### 17.3 Smartup zakaz statuslari (otgruzka)
`D` (Draft) → `B#N` (New) → `B#E` (In progress) → `B#W` (Waiting to ship) → `B#S` (Shipped) → `B#V` (Delivered) → `A`/`C`

---

*Hujjat oxiri — v0.1. Keyingi qadam: yuqoridagi 16-bo'lim savollariga javob va har modul bo'yicha batafsil funksional ssenariylar (use-case) + ERD.*
