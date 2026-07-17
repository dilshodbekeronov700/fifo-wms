# Smartup API — to'liq ma'lumotnoma (sklad 100% qamrov)

> Manba: rasmiy Postman hujjati `https://api.greenwhite.uz` (collection `38039337/2sAXxP8Xzx`),
> "Smartup API Documentation". Yuklab olingan: 2026-06-25. Bu WMS (Green White suv zavodi)
> integratsiyasi uchun. Asl Belgisi tomoni: `aslbelgisi_integration.md`.

## ⭐ Tashkilot modeli (Single vs Head Organization) — KRITIK
Overview'dan (2026-06-26 to'liq o'qildi). Bu OCARD'dagi `filial_code` xatolarining ildiz sababi:
- **`filial_id` header** = Single Organization YOKI Head Organization ning ID'si:
  - **Single org** tanlansa → barcha so'rovlar SHU tashkilotga bog'lanadi. Boshqa single orglarga
    kirib bo'lmaydi. Body'dagi `filial_code` bilan boshqa tashkilotга O'TIB BO'LMAYDI (mos kelmasa
    `A02-24-048` "организация не соответствует текущей"). Kodi null bo'lsa, har qanday filial_code rad etiladi.
  - **Head org** tanlansa → so'rovlar body'dagi `filial_code` bo'yicha ishlaydi; `filial_code` bo'sh
    bo'lsa → BARCHA tashkilotlar bo'yicha. ← `01-OCARD` va boshqa 17 ta orgga kirish uchun KERAK.
- OCARD holati: `filial_id=1833` = bitta **single org** (ichki id 19048551, kodi null). Shuning uchun
  `filial_code=01-OCARD` ishlamaydi. `01-OCARD`/Ташкент (skladlar 02/07/19) uchun **Head org'ning
  filial_id'si** kerak (Smartup admin/integratsiya sozlamasidan).
- **Limitlar (rasmiy):** References 100/kun, kam ishlatiladigan hujjat 300/kun, tez-tez 500/kun.
  Data oynasi: faqat oxirgi **7 kun**. Import: ≤**5000** obyekt/so'rov. So'rov javobida `limits{}` obyekti
  (has_limit, limit_quant, object_count, day_range_limit, request_quant, left_limit_quant).
- **project_code** qiymatlari: `trade`, `anor`, `clinic`, `telecom`, … (loyihani aniqlaydi).

> 📄 Har bir endpoint to'liq body+sxema bilan: `smartup_api_reference_full.md` (63 endpoint, Postman'dan auto).

## Asoslar
- **Base URL:** `https://smartup.online`
- **Auth:** HTTP Basic (base64 `login:password`) — collection darajasida.
- **Headers:** `project_code` (trade endpointlarida `trade`), `filial_id` (Green White = **1833**;
  hujjat namunalarida 86401/86 — demo qiymatlar). Import'larda `Content-Type: application/json`.
- **Sanalar:** `dd.mm.yyyy`. Vaqt maydonlari ham shu format (ba'zilarida `dd.mm.yy`).
- **Inkremental sync:** `begin_modified_on`/`end_modified_on`, `begin_created_on`/`end_created_on`,
  va hujjatga xos `begin_<x>_date`/`end_<x>_date`.
- **Idempotentlik:** har bir obyektda `external_id` (3rd-party tomon ID'si).
- **Bulk:** barcha interfeyslar bitta so'rovda ko'p obyekt qabul qiladi.
- **inventory_kind:** `G`=tovar (goods), `M`=xom ashyo (raw materials), `P`=mahsulot (products).
  Deyarli barcha hujjat item'larida bor.
- **Import javobi (standart):** `{ "successes": [{"code": ""}], "errors": [] }`
- **Status kodlari (hujjatlarda):** `D`=draft, `A`=active/approved, `C`=confirmed/completed,
  `T`=tranzit, `B`=booked, `F`=free (balance filtri uchun).

---

## 1. WAREHOUSE (sklad) — 8 ta bo'lim

### 1.1 Receipts to warehouse (zavod kirimi) — `mkw/input`
- **Import:** `POST b/anor/mxsx/mkw/input$import`
  - body: `{ input:[{ filial_code, external_id, input_id, input_number, input_time(dd.mm.yyyy),
    status(D/A/C), warehouse_code, note, input_items:[{ external_id, input_item_id, purchase_id,
    purchase_item_id, quantity, marking_codes:[{marking_code}] }] }] }`
- **Export:** `POST b/anor/mxsx/mkw/input$export`
  - body: `{ filial_codes:[{filial_code}], filial_code, external_id, input_id,
    begin_input_date, end_input_date, begin_created_on, end_created_on,
    begin_modified_on, end_modified_on, producer_codes:[] }`

### 1.2 Purchase (xarid) — `mkw/purchase`
- **Import:** `POST b/anor/mxsx/mkw/purchase$import`
  - body: `{ purchase:[{ filial_code, external_id, purchase_id, purchase_number,
    purchase_time, order_id, status_code, input_date, supplier_code, contract_code,
    warehouse_code, currency_code, invoice_number, invoice_date, total_margin_kind,
    total_margin_value, note, posted, purchase_items:[{ external_id, purchase_item_id,
    product_code, order_item_id, on_balance, serial_number, inventory_kind, card_code,
    expiry_date, quantity, price, margin_kind, margin_value, vat_percent, vat_amount }] }] }`
- **Export:** `POST b/anor/mxsx/mkw/purchase$export`
  - body: `{ filial_codes, filial_code, external_id, purchase_id, begin_purchase_date,
    end_purchase_date, begin_created_on, end_created_on, begin_modified_on, end_modified_on }`

### 1.3 Internal movement (ichki ko'chirish, sklad↔sklad) — `mkw/movement`
- **Import:** `POST b/anor/mxsx/mkw/movement$import`
  - body: `{ movement:[{ filial_code, external_id, movement_id, request_id, movement_number,
    from_movement_date, to_movement_date, status(C…), from_warehouse_code, to_warehouse_code,
    reason_code, note, barcode, movement_items:[{ external_id, movement_item_id, request_item_id,
    product_code, inventory_kind(G), card_code, serial_number, expiry_date, on_balance,
    quantity, batch_number }] }] }`
- **Export:** `POST b/anor/mxsx/mkw/movement$export`
  - body: `{ filial_codes, filial_code, external_id, movement_id, begin_from_movement_date,
    end_from_movement_date, begin_to_movement_date, end_to_movement_date,
    begin_created_on, end_created_on, begin_modified_on, end_modified_on }`

### 1.4 Cross-organizational movement (tashkilotlararo) — `mfm/movement`
- **Import:** `POST b/anor/mxsx/mfm/movement$import`
  - body: `{ movement:[{ from_filial_code, external_id, movement_id, subfilial_code,
    to_subfilial_code, from_room_code, from_robot_code, from_robot_person_code,
    from_warehouse_code, from_time, to_filial_code, to_warehouse_code, to_time,
    currency_code, price_type_code, payment_type_code, cash_register_id, request_id,
    reason_id, note, barcode, amount, amount_base, delivery_number, contract_code, status,
    movement_items:[{ external_id, movement_unit_id, request_item_id, from_inventory_kind,
    on_balance, to_inventory_kind, product_code, card_code, expiry_date, serial_number,
    quantity, price, amount, amount_base, margin_kind, margin_value, margin_amount,
    vat_percent, vat_amount, load_id }] }] }`
- **Export:** `POST b/anor/mxsx/mfm/movement$export`
  - body: `{ filial_codes, filial_code, external_id, movement_id, begin_from_date,
    end_from_date, begin_to_date, end_to_date, begin_created_on, end_created_on,
    begin_modified_on, end_modified_on }`
- **Status change:** `POST b/anor/mxsx/mfm/movement$change_status`
  - body: `{ movement:[{ movement_id, status }] }`

### 1.5 Stocktaking (inventarizatsiya) — `mkw/stocktaking`
- **Import:** `POST b/anor/mxsx/mkw/stocktaking$import`
  - body: `{ stocktaking:[{ filial_code, external_id, stocktaking_id, stocktaking_number,
    stocktaking_date(dd.mm.yyyy), status(D…), warehouse_code, currency_code, reason_code,
    note, stocktaking_items:[{ external_id, stocktaking_item_id, product_code, serial_number,
    inventory_kind(G), card_code, expiry_date, batch_number, quantity, income_price }] }] }`
  - Eslatma: `quantity` = real sanab chiqilgan miqdor (balance bilan solishtiriladi).
- **Export:** `POST b/anor/mxsx/mkw/stocktaking$export`
  - body: `{ filial_codes, filial_code, external_id, stocktaking_id, begin_stocktaking_date,
    end_stocktaking_date, begin_created_on, end_created_on, begin_modified_on, end_modified_on }`

### 1.6 Write-off (spisaniye) — `mkw/writeoff`
- **Import:** `POST b/anor/mxsx/mkw/writeoff$import`
  - body: `{ writeoff:[{ filial_code, external_id, writeoff_id, writeoff_number,
    writeoff_date, status, warehouse_code, reason_code, currency_code, note,
    writeoff_items:[{ external_id, writeoff_item_id, product_code, serial_number,
    inventory_kind, card_code, expiry_date, quantity, batch_number }] }] }`
- **Export:** `POST b/anor/mxsx/mkw/writeoff$export`
  - body: `{ filial_codes, filial_code, external_id, writeoff_id, begin_writeoff_date,
    end_writeoff_date, begin_created_on, end_created_on, begin_modified_on, end_modified_on }`

### 1.7 Return to suppliers (postavshchikka qaytarish) — `mkw/return`
- **Import:** `POST b/anor/mxsx/mkw/return$import`
  - body: `{ return:[{ filial_code, external_id, return_id, return_number, return_time,
    status(D…), warehouse_code, reason_code, currency_code, supplier_code, owner_person_code,
    contract_code, purchase_id, invoice_number, invoice_date, note,
    return_items:[{ external_id, return_item_id, purchase_item_id, input_id, input_item_id,
    serial_number, inventory_kind(G), on_balance, product_code, card_code, expiry_date,
    quantity, price, margin_kind, margin_value, vat_percent, vat_amount }] }] }`
- **Export:** `POST b/anor/mxsx/mkw/return$export`
  - body: `{ filial_codes, filial_code, external_id, return_id, begin_return_date,
    end_return_date, begin_created_on, end_created_on, begin_modified_on, end_modified_on }`

### 1.8 Logistics — `trade/txs/tdeal/logistics`
- **Import:** `POST b/trade/txs/tdeal/logistics$import`
  - body: `{ logistics:[{ logistics_id, external_id, delivery_date, expeditor_code,
    van_code, lap, deals:[{deal_id}] }] }`
- **Export:** `POST b/trade/txs/tdeal/logistics$export`
  - body: `{ logistics_id, external_id, delivery_date, expeditor_code, van_code,
    begin_created_on, end_created_on, begin_modified_on, end_modified_on }`
  - javob qo'shimcha: expeditor_name, van_name, begin/end_location, cash_register_id/name,
    deals[].status.
- **Attach cash register to van:** `POST b/trade/txs/tdeal/logistics$attach_cash_register`
  - body: `{ van_id, cash_register_id }` (eslatma: namunada host `app3.gw.greenwhite.uz/xtrade`).

---

## 2. OTHERS — Balance (qoldiq / svereka) ⭐ ENG MUHIM

### 2.1 Inventory Balance / Export — `mkw/balance`
- `POST b/anor/mxsx/mkw/balance$export`
- **body:** `{ warehouse_codes:[{warehouse_code}], filial_code,
  product_conditions:["T","B","F"], begin_date(dd.mm.yyyy, REQUIRED),
  end_date(dd.mm.yyyy, REQUIRED), producer_codes:[] }`
  - `product_conditions`: `F`=free (erkin), `B`=booked (bron), `T`=tranzit.
  - `begin_date`/`end_date` — **majburiy**; balans "one-day principle" bilan ishlaydi.
- **javob:** `{ balance:[{ date, warehouse_id, warehouse_code, product_code, product_id,
  card_code, expiry_date, serial_number, batch_number, inventory_kind(G/M/P), quantity,
  input_price, measure_code, groups:[{group_code,type_code}], producer_code, currency_code,
  base_price }] }`
  - `card_code`/`expiry_date` bir xil bo'lsa — tizim 1 deb sanaydi.

### 2.2 Equipment Balance / Export — `trade/txs/tvt/equipment_balance`
- `POST b/trade/txs/tvt/equipment_balance$export_data`  (headers: `filial_id`, `project_code=trade`)
- body: `{ offset, limit(max 50), filial_code, room_codes:[{room_code}],
  product_group_codes:[{product_group_code}], product_type_codes:[{product_type_code}],
  product_codes:[{product_code}] }`
- javob: `{ count, data:[{ filial_name, installed_date, equipment_name, serial_number,
  equipment_status, warehouse_name, person_*, room_name, last_visit_date, has_barcode, … }] }`

---

## 3. SALE / Order (chiqim, picking, marking biriktirish)

- **Order Export:** `POST b/trade/txs/tdeal/order$export` (headers: `project_code=trade, filial_id=1833`)
  - body: `{ filial_codes, filial_code, external_id, deal_id, begin_deal_date, end_deal_date,
    delivery_date, begin_created_on, end_created_on, begin_modified_on, end_modified_on }`
  - javob: `order[]`, qatorlar `order_products[]`, `person_tin`, `with_marking`,
    `marking_attaching_method`.
- **Order Import:** `POST b/trade/txs/tdeal/order$import`
  - body: `{ order:[{ filial_code, external_id, deal_id, subfilial_code, delivery_number,
    delivery_date, room_code, robot_code, deal_time, status(A…), sales_manager_code,
    person_code, currency_code, owner_person_code, van_code, contract_code, note,
    self_shipment, delivery_address_short, delivery_address_full, marking_attaching_method,
    invoice_number, expeditor_code, payment_type_code,
    order_products:[{ external_id, product_unit_id, inventory_kind(G), warehouse_code,
    product_code, serial_number, card_code, expiry_date, on_balance, order_quant, … }] }] }`
- **Order Attach Data:** `POST b/trade/txs/tdeal/order$attach_data`
  - body: `{ order:[{ deal_id, delivery_number, expeditor_code, van_code, self_shipment,
    note, marking_attaching_method }] }`
- **Order Status Change:** `POST b/trade/txs/tdeal/order$change_status`
  - body: `{ order:[{ deal_id, status }] }`
- **Order Attach Marking Codes:** `POST b/anor/mxsx/mdeal/order$import_order_marking_codes`
  - body: `{ deal_id, products:[{ product_unit_id, marking_codes:[] }] }`

### Sale boshqa: Return (`mdeal/return$import|$export`), Visit (`…/visit$export`).

---

## 4. REFERENCES — Inventory (master data) ⭐

### Inventory Import — `mr/inventory`
- `POST b/anor/mxsx/mr/inventory$import` (header: `project_code=trade`)
- body: `{ inventory:[{ inventory_id, product_id, code(REQUIRED, unik), name(REQUIRED),
  short_name, weight_netto, weight_brutto, litr, box_type_code, box_quant(qadoqdagi dona),
  producer_code, measure_code(REQUIRED), state(A/P), barcodes, order_no, article_code,
  gtin, ikpu, tnved, marking_group_code, groups:[{group_code,type_code}],
  inventory_kinds:[{inventory_kind}], sector_codes:[{sector_code}] }] }`
- **Export:** `POST b/anor/mxsx/mr/inventory$export`
  - body: `{ code, begin_created_on, end_created_on, begin_modified_on, end_modified_on }`
  - javob: yuqoridagi maydonlar (WMS uchun muhim: `code`, `name`, `gtin`, `ikpu`,
    `box_quant`→units_per_box, `measure_code`, `marking_group_code`, `weight_netto/brutto`, `litr`).

### Boshqa References (12 ta, barchasi `$import`+`$export`):
Service (`mr/...`), Product group, Price type, Inventory price, Producers, Legal entity,
Natural persons, Persons group, Workspaces (faqat export), Contract, Return Reason.

---

## 5. To'liq endpoint ro'yxati (qamrov tekshiruvi)
**Documents → Sale:** Order Import/Export/AttachData/StatusChange/AttachMarkingCodes, Return Import/Export, Visit Export.
**Documents → Warehouse (8):** Cross-org movement Import/Export/StatusChange, Internal movement Import/Export,
Stocktaking Import/Export, Write-off Import/Export, Return-to-suppliers Import/Export,
Receipts Import/Export, Purchase Import/Export, Logistics Import/Export/AttachCashRegister.
**Documents → Finance:** Payments-from-clients, Cash Operations, Bank Statements (har biri Import/Export).
**Documents → Equipment:** Equipment movement Import/Export/Change, Equipment request Import/Export/Change.
**References (12):** Inventory, Service, Product group, Price type, Inventory price, Producers,
Legal entity, Natural persons, Persons group, Workspaces, Contract, Return Reason.
**Others:** Inventory Balance Export, Equipment Balance Export.

## 6. Kod bilan moslik (wms/app/connectors/smartup.py) — 2026-06-25 holati
Koddagi barcha yo'llar hujjatga MOS (tekshirilgan):
`tdeal/order$export`, `mdeal/order$import_order_marking_codes`, `tdeal/order$change_status`,
`mkw/balance$export`, `mkw/input$export`, `mkw/movement$import`, `mkw/stocktaking$import`,
`mkw/writeoff$import`, `mr/inventory$export`.
