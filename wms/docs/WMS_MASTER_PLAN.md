# WMS — Master Plan: Smartup maksimal integratsiya + UI/UX kuchaytirish

> Maqsad: Smartup'dan WMS uchun kerakli BARCHA oqimlarni to'liq ishlatish + har bir bo'limni
> UI/UX jihatdan (qidiruv, filtr, saralash, bulk, eksport) mayda detallargacha kuchaytirish.
> Tartib: avval backend integratsiya (funksional), keyin bo'lim-bo'lim UI/UX, oxirida kesishuvchi.

Holat: ✅ tayyor · 🟡 jarayonda · ⬜ rejada

## FAZA A — Smartup integratsiya (to'liq ishlash)
Connector qatlami TAYYOR (get_purchases, get_movements, get_cross_org_movements, get_stocktakings,
get_writeoffs, get_supplier_returns, get_sale_returns, post_*, change_*). Yetishmaydi: sync-servis + endpoint + UI.

- A1 ✅ **Xaridlar (purchase$export) → Kirim** — distributor uchun ASOSIY kirim. sync_purchases + endpoint + Receipt UI.
- A2 ✅ Buyurtma status push (order$change_status) + marka biriktirish — Chiqim → Smartup.
- A3 ✅ Ko'chirish (ichki + tashkilotlararo movement) — UI + endpoint.
- A4 ✅ Inventarizatsiya (stocktaking$export/$import) — Qoldiqlar/Vazifalar.
- A5 ✅ Spisaniye + Vozvrat (writeoff, sale/supplier return) — Operatsiyalar/Kirim/Chiqim.
- A6 ⬜ Balans org-config bardoshliligi — friendly xato (✅ qisman), Settings'da "Test" ulangan org'ni ko'rsatsin.

## FAZA B — Bo'lim-bo'lim UI/UX
- B0 ✅ Qayta ishlatiladigan **FilterBar/SearchInput/DataTable** komponentlari (saralash, ustun, bo'sh-holat, skelet).
- B1 ✅ Mahsulotlar: qidiruv (nom/GTIN/kod), filtr (kategoriya/marka/faol/qoldiq), saralash, bulk, eksport.
- B2 ✅ Kirim: filtr (ta'minotchi/sana/status/markirovka), TSD progress, nomuvofiqlik.
- B3 ✅ Chiqim: qidiruv (mijoz/STIR/№), filtr (status/sana/summa/markirovka/stock), tayyorlik indikatori.
- B4 ✅ Qoldiqlar: qidiruv/filtr (sklad/zona/farqli/muddat), FEFO saralash.
- B5 ✅ Vazifalar: filtr (tur/ijrochi/status/ustuvorlik), Kanban.
- B6 ⬜ Ko'chirish: filtr (qayerdan→qayerga/status/sana).
- B7 ✅ Boshqaruv paneli: KPI kartalar + drill-down (filtrlangan o'tish), real-time.
- B8 ✅ Analitika: filtr (sana/sklad/mahsulot/operator), ABC, KPI, eksport.
- B9 ✅ Harorat-namlik: filtr (sensor/zona/chegara), jonli grafik, alert.
- B10 ❌ Yorliqlar (printer/ZPL) — OLIB TASHLANDI (web/TSD'dan kerak emas, foydalanuvchi qarori).
- B11 ✅ Sklad xarita/3D: qidiruv→highlight, filtr (zona/band/harorat).
- B12 ✅ Sozlamalar: Smartup test→org ko'rsatish, sklad↔kod mapping jadvali, sync interval, rol/audit.

## FAZA C — Kesishuvchi
- C1 ✅ Global qidiruv (⌘K) — mahsulot/buyurtma/yacheyka/partiya.
- C2 🟡 Saqlanadigan filtrlar + URL'ga yozish + filtr chiplari.
- C3 ✅ CSV/Excel eksport (jadvallarda).
- C4 ✅ Klaviatura tezkor tugmalari (TSD/operator).

## Bajarilish tartibi (ustuvorlik)
A1 → A2 → B0 → B3 → B1 → B4 → A3 → A4 → B5 → B7 → A5 → B2/B6/B8-B12 → C1-C4.
