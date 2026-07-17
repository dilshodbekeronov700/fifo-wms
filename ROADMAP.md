# 🏭 WMS Raqamlashtirish — To'liq Roadmap

> Maqsad: Green White suv zavodi sklad jarayonlarini to'liq raqamlashtirish.
> Komponentlar: **Web WMS** (FastAPI + React) · **TSD** (Android skaner) · **Smartup ERP** · **Asl Belgisi** (xtrace marking) · **IoT sensorlar** (ESP32 + DHT-21).
> Ish uslubi: bosqichma-bosqich, har biri tugagach ko'rsatiladi.

---

## Hozirgi holat (tayyor)
- ✅ Backend B1: auth, RBAC, Ledger, warehouse/zone/location CRUD
- ✅ Smartup: mahsulot sync, qoldiq svereka (admin@ocard, 15 mahsulot), buyurtma→picking, kirim, push (movement/writeoff/stocktaking), outbox
- ✅ Asl Belgisi: connector (KIZ tekshirish, marking)
- ✅ TSD: skaner (clipboard/keyboard/intent), putaway, receipt, inventory, picking, offline navbat
- ✅ 540 real yacheyka, 2D layout + 3D twin (PDF rejaga mos)

---

## FAZA 1 — Xaritani birlashtirish + To'liq Muharrir  ⭐ (boshlash shu yerdan)
**Muammo:** xarita 3 joyda (Warehouses, /map, /twin3d) — chalkash.
**Yechim:** bitta **"Sklad"** markazi, 3 tab: **Xarita (2D, tahrirlanadigan)** · **3D Twin** · **Ro'yxat**.

### 1.1 Backend — kengaytirilgan model
`Location` va `Zone`ga tahrir maydonlari:
- O'lcham: `length_mm`, `width_mm`, `height_mm`
- Sig'im: `max_weight_kg`, `max_pallets` (bor)
- Joylashuv: `row`, `rack`, `tier`, `position`, `x`, `y`, `rotation`
- Rack guruhi: `rack_group` (segment id)
- Yangi endpointlar: bulk create/update/delete locations, "rack generator" (N ustun × M etaj × K pallet)

### 1.2 Frontend — interaktiv muharrir
- Grid'da rack qo'shish/o'chirish/sudrash/burish
- Yacheyka tanlab — yon panelda barcha maydonni tahrirlash (kod, etaj, pallet, o'lcham, balandlik, og'irlik)
- "Generatsiya" sehrgari: bitta rack'dan butun blok yaratish
- Saqlash → 2D va 3D darhol yangilanadi
- Eski 2 sahifa (Warehouses embed, /map) olib tashlanadi / yo'naltiriladi

---

## FAZA 2 — 3D Digital Twin (wow)
- Yacheyka bosilsa → mahsulot, partiya, muddat, qoldiq, og'irlik
- **Issiqlik xaritasi rejimlari:** band/bo'sh · FEFO (muddat) · ABC · og'irlik · **harorat** (IoT bilan bog'liq)
- Qidiruv: "Blanc Bleu 0.5 qayerda?" → 3D'da yoritadi
- Forklift marshrut animatsiyasi, kamera presetlari (yuqoridan/yon/aylanma)
- Real-time yangilanish (SSE)

---

## FAZA 3 — IoT Harorat/Namlik monitoring  🌡️ (YANGI)
**Apparat:** ESP32-S3-DevKitC-1 + DHT-21 (harorat/namlik) + SSD1306 OLED.

### 3.1 Backend
- `Sensor` modeli: id, nomi, zona/lokatsiya bog'lanishi, turi, holati, oxirgi ko'rinish
- `SensorReading` modeli: sensor_id, harorat, namlik, vaqt
- **Ingest endpoint:** `POST /api/v1/telemetry` (ESP32 HTTP bilan yuboradi) — API-key auth
- Real-time: SSE orqali jonli uzatish (mavjud `realtime.py`)
- **Threshold alert:** harorat/namlik chegaradan chiqsa → ogohlantirish (masalan suv uchun 5–25°C)
- Tarix: vaqt bo'yicha grafik, min/max/o'rtacha

### 3.2 Frontend
- **Monitoring dashboard:** har sensor jonli kartochka (harorat, namlik, holat, oxirgi yangilanish)
- Tarix grafiklari (recharts), zona bo'yicha
- 3D Twin'da zonalarni **harorat rangi** bilan ko'rsatish
- Ogohlantirishlar tarmog'i (chegaradan chiqqanda qizil + bildirishnoma)

### 3.3 Firmware (ESP32)
- Arduino sketch: DHT-21 o'qish → OLED'da ko'rsatish → WMS'ga POST (Wi-Fi)
- Konfiguratsiya: Wi-Fi, WMS URL, sensor API-key, interval
- `/firmware/esp32_dht21/` papkasida tayyor kod + ko'rsatma

---

## FAZA 4 — Analitika va Hisobotlar  📊 (KUCHAYTIRILGAN)
> Alohida e'tibor — chuqur, foydali, eksport qilinadigan.

### 4.1 KPI Dashboard (boshqaruv uchun)
- Sklad to'ldirilishi (%), aylanma (turnover), o'rtacha saqlash muddati
- Kirim/chiqim hajmi (kunlik/haftalik/oylik trend)
- Picking tezligi, xodim unumdorligi, xatolar darajasi
- FEFO buzilishlari, muddati tugagan tovar yo'qotishlari

### 4.2 Hisobotlar (eksport: Excel/PDF/CSV)
- **Qoldiq hisoboti** (zona/mahsulot/partiya bo'yicha)
- **Harakat hisoboti** (kirim/chiqim/ko'chirish/spisaniye)
- **Svereka hisoboti** (WMS ↔ Smartup farqlari)
- **Muddat hisoboti** (FEFO — tugayotganlar ro'yxati)
- **IoT hisoboti** (harorat/namlik tarixi, buzilishlar)
- **ABC tahlili** (mahsulot aylanmasi bo'yicha tasnif)
- Sana oralig'i, filtr, jadval + grafik, har birini yuklab olish

### 4.3 Vizualizatsiya
- Issiqlik xaritalari, trend grafiklari, taqsimot diagrammalari
- Avtomatik haftalik/oylik hisobot (jadval bo'yicha email/eksport)

---

## FAZA 5 — Smartup maksimal integratsiya
- Avto-sinxron (jadval: mahsulot kunlik, qoldiq svereka kunlik)
- Buyurtma → picking to'liq oqim (status qaytarish)
- Ikki tomonlama: WMS movement/writeoff/inventar → Smartup push (outbox, bor)
- Vozvrat (return) tortish
- Sklad kodlarini avtomatik moslash (`warehouse$export`)
- Integratsiya holati paneli (oxirgi sync, xatolar, navbat)

---

## FAZA 6 — Asl Belgisi maksimal
- Qabulda KIZ (DataMatrix) skanlab → egalik + mahsulot tekshirish
- Agregatsiya zanjiri: birlik → quti → pallet → transport
- Chiqimda kod biriktirish + status
- FEFO avtomatik (muddat marking'dan)
- Marking holati paneli (RECEIVED/SHIPPED/...)

---

## FAZA 7 — TSD takomillashtirish
- Barcha oqimlar: kirim, joylash, ko'chirish, picking, inventarizatsiya, svereka
- Ovozli/vibratsiya feedback, katta tugmalar, offline (bor)
- Vazifa ro'yxati (tasklar) + push bildirishnoma
- IoT: TSD'da zona haroratini ko'rish

---

## FAZA 8 — UX / Dizayn / Onboarding (wow)
- Birinchi kirishda **onboarding** sayohati
- Izchil dizayn tizimi (ranglar, komponentlar, ikonkalar)
- Aniq bosh dashboard: bugungi vazifalar, ogohlantirishlar, KPI, IoT holati
- Bo'sh holatlar uchun yo'l-yo'riq, tooltip, qidiruv (global)
- Til: O'zbek/Rus/Ingliz (bor) — to'liq tarjima
- Mobil-moslik, tez, chiroyli animatsiyalar

---

## Texnik ketma-ketlik
1. **Faza 1** (xarita birlashtirish + muharrir) — poydevor
2. **Faza 3** (IoT) — apparat keldi, parallel boshlanadi
3. **Faza 2** (3D twin) — Faza 1 model'iga tayanadi
4. **Faza 4** (analitika/hisobot) — barcha ma'lumot yig'ilgach kuchayadi
5. **Faza 5–6** (Smartup/Asl Belgisi chuqurlashtirish)
6. **Faza 7–8** (TSD + UX sayqal)

> Har faza tugagach: ishlayotgan demo + qisqa hisobot.
