"""
Smartup ERP connector — verified against the official Green White API docs.

Base URL: https://smartup.online
Auth: Basic Auth (base64 login:password) + headers project_code, filial_id.

Path families:
  - Trade docs:  b/trade/txs/...
  - Anor docs:   b/anor/mxsx/...
Dates: dd.mm.yyyy · incremental: begin_/end_modified_on · idempotency: external_id
Limits: References 100/day, infrequent 300/day, frequent 500/day; 7-day window;
import ≤5000 objects/request.
"""
from __future__ import annotations

import base64
from dataclasses import dataclass, field
from typing import Any

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.core.circuit import CircuitBreaker, get_breaker


class SmartupApiError(Exception):
    """Smartup HTTP xatosi — UI'da aniq ko'rinishi uchun (status + xabar)."""

    def __init__(self, status: int, body: str) -> None:
        self.status = status
        self.body = (body or "").strip()
        super().__init__(f"Smartup {status}: {self.body[:200]}")


@dataclass
class SmartupOrderLine:
    product_unit_id: str
    product_code: str
    gtin: str | None
    qty_ordered: float
    uom: str
    deal_id: str
    product_name: str | None = None   # Smartup order_products'da BOR (product_name)
    expiry_date: str | None = None    # order_products qatoridan (FEFO uchun)
    product_price: float | None = None   # birlik narxi
    price_type_code: str | None = None   # narx turi (Тип цены)
    vat_percent: float | None = None     # QQS %
    batch_number: str | None = None      # partiya raqami
    warehouse_code: str | None = None    # sklad kodi (qator darajasida)
    sold_amount: float | None = None     # qator summasi


@dataclass
class SmartupOrder:
    deal_id: str
    order_number: str
    status: str          # D=qoralama B#N=yangi B#E=jarayonda B#W=kutilmoqda B#S=jo'natilgan B#V=YETKAZILGAN (Доставлен) · C/A faol ro'yxatda yo'q
    customer_tin: str | None
    with_marking: str | None
    customer_name: str | None = None   # person_name — UI'da ko'rsatish uchun
    total_amount: float | None = None  # total_amount — buyurtma summasi
    order_date: str | None = None      # deal_time — buyurtma sanasi
    delivery_date: str | None = None   # delivery_date — yetkazish sanasi
    # ── Smartup "Заказы" ustunlari bilan to'liq moslik uchun ──
    working_zone: str | None = None       # room_name — Рабочая зона
    payment_type_code: str | None = None  # PYMT:1/PYMT:3/… — Тип оплаты
    price_type_code: str | None = None    # birinchi qatordan — Тип цены
    delivery_address: str | None = None   # delivery_address_full/short
    delivery_number: str | None = None    # yetkazish/nakladnaya raqami
    contract_number: str | None = None    # shartnoma raqami
    note: str | None = None               # note / deal_note — Примечания
    discount_value: float | None = None   # deal_margin_value — skidka/naценка
    discount_kind: str | None = None      # deal_margin_kind (P=%, ...)
    weight_netto: float | None = None     # total_weight_netto — Вес нетто
    weight_brutto: float | None = None    # total_weight_brutto — Вес брутто
    litre: float | None = None            # total_litre — Литры
    sales_manager_name: str | None = None # sales_manager_name — menejer
    expeditor_name: str | None = None     # expeditor_name — ekspeditor
    driver_name: str | None = None        # driver_name — haydovchi
    self_shipment: str | None = None      # self_shipment (Y/N)
    lines: list[SmartupOrderLine] = field(default_factory=list)


class SmartupClient:
    """Async client for the Smartup ERP REST API."""

    def __init__(
        self,
        base_url: str,
        login: str,
        password: str,
        project_code: str,
        filial_id: str,
        filial_code: str = "",
    ) -> None:
        self._base = base_url.rstrip("/")
        self.project_code = project_code
        self.filial_id = filial_id
        # filial_code = Smartup tashkilot KODI (balance$export uchun majburiy).
        # filial_id (header) bilan ADASHTIRMANG. Masalan: "01-OCARD".
        self.filial_code = filial_code
        _creds = base64.b64encode(f"{login}:{password}".encode()).decode()
        self._headers = {
            "Authorization": f"Basic {_creds}",
            "filial_id": str(filial_id),
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        # project_code faqat to'ldirilgan bo'lsa yuboriladi.
        # (Ba'zi endpointlarda noto'g'ri project_code "Требуется авторизация" beradi;
        #  bo'sh qoldirilsa akkauntning standart loyihasi ishlatiladi.)
        if project_code and project_code.strip():
            self._headers["project_code"] = project_code.strip()

    @property
    def _breaker(self) -> "CircuitBreaker":
        return get_breaker(f"smartup:{self._base}")

    # Faqat tarmoq xatosida qayta urinamiz; HTTP 4xx/5xx aniq xabar bilan chiqadi.
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=15),
        retry=retry_if_exception_type((httpx.TransportError, httpx.TimeoutException)),
    )
    async def _post_raw(self, path: str, payload: dict) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{self._base}/{path.lstrip('/')}", json=payload, headers=self._headers
            )
            if resp.status_code >= 400:
                raise SmartupApiError(resp.status_code, resp.text)
            return resp.json()

    async def _post(self, path: str, payload: dict) -> dict[str, Any]:
        # Circuit tashqarida: tarmoq xatosi yoki 5xx = ishlamay qolish (sanaladi),
        # 4xx = mijoz xatosi (circuit'ni ochmaydi).
        br = self._breaker
        br.before_call()
        try:
            data = await self._post_raw(path, payload)
        except SmartupApiError as exc:
            if exc.status >= 500:
                br.on_failure()
            else:
                br.on_success()
            raise
        except Exception:
            br.on_failure()
            raise
        br.on_success()
        return data

    async def _export(
        self,
        path: str,
        root_key: str,
        *,
        warehouse_codes: list[str] | None = None,
        begin_modified_on: str | None = None,
        end_modified_on: str | None = None,
        extra: dict | None = None,
    ) -> list[dict]:
        """Umumiy $export envelope — barcha pull oqimlari uchun (DRY).

        Smartup $export so'rovlari bir xil inkremental konvertdan foydalanadi:
        filial_codes[] + begin/end_modified_on. `extra` orqali hujjatga xos
        filtrlar (masalan begin_*_date) qo'shiladi. Javobning `root_key` massivi
        qaytariladi.
        """
        body: dict[str, Any] = dict(extra or {})
        if warehouse_codes:
            body["filial_codes"] = [{"filial_code": c} for c in warehouse_codes]
        if begin_modified_on:
            body["begin_modified_on"] = begin_modified_on
        if end_modified_on:
            body["end_modified_on"] = end_modified_on
        data = await self._post(path, body)
        return data.get(root_key, [])

    # ── Orders (otgruzka) ────────────────────────────────────────────────────
    async def get_orders(
        self,
        statuses: list[str] | None = None,
        warehouse_codes: list[str] | None = None,
        begin_modified_on: str | None = None,
        end_modified_on: str | None = None,
    ) -> list[SmartupOrder]:
        body: dict[str, Any] = {}
        if statuses:
            body["statuses"] = statuses
        # Buyurtmalar TASHKILOT (filial) darajasida — sklad kodi filial EMAS.
        # (Sklad bo'yicha filtr order_products ichida; bu yerda butun filial olamiz.)
        if self.filial_code:
            body["filial_code"] = self.filial_code
        if begin_modified_on:
            body["begin_modified_on"] = begin_modified_on
        if end_modified_on:
            body["end_modified_on"] = end_modified_on

        data = await self._post("b/trade/txs/tdeal/order$export", body)
        orders: list[SmartupOrder] = []
        for raw in data.get("order", []):
            deal_id = str(raw.get("deal_id", ""))
            def _f(v: Any) -> float | None:
                try:
                    return float(v) if v not in (None, "") else None
                except (TypeError, ValueError):
                    return None

            raw_lines = raw.get("order_products", [])
            lines = [
                SmartupOrderLine(
                    product_unit_id=str(ln.get("product_unit_id", "")),
                    # Ba'zi order qatorlarida product_code BO'SH keladi (masalan Karlovy
                    # 0,33 GROUP) — lekin product_barcode = WMS smartup_product_code.
                    # Shuning uchun kod bo'sh bo'lsa barcode'ni kod sifatida ishlatamiz.
                    product_code=str(ln.get("product_code") or ln.get("product_barcode") or ""),
                    gtin=ln.get("gtin") or None,
                    qty_ordered=float(ln.get("order_quant") or ln.get("quant") or ln.get("qty") or 0),
                    uom=ln.get("measure_code") or ln.get("uom", "unit"),
                    deal_id=deal_id,
                    product_name=ln.get("product_name") or None,
                    expiry_date=(ln.get("expiry_date") or None),
                    product_price=_f(ln.get("product_price")),
                    price_type_code=ln.get("price_type_code") or None,
                    vat_percent=_f(ln.get("vat_percent")),
                    batch_number=ln.get("batch_number") or None,
                    warehouse_code=ln.get("warehouse_code") or None,
                    sold_amount=_f(ln.get("sold_amount")),
                )
                for ln in raw_lines
            ]
            first_price_type = next(
                (ln.get("price_type_code") for ln in raw_lines if ln.get("price_type_code")), None
            )
            orders.append(SmartupOrder(
                deal_id=deal_id,
                order_number=str(raw.get("invoice_number") or raw.get("delivery_number") or ""),
                status=str(raw.get("status", "")),
                customer_tin=raw.get("person_tin"),
                with_marking=raw.get("with_marking"),
                customer_name=raw.get("person_name") or None,
                total_amount=_f(raw.get("total_amount")),
                order_date=raw.get("deal_time") or None,
                delivery_date=raw.get("delivery_date") or None,
                working_zone=raw.get("room_name") or None,
                payment_type_code=raw.get("payment_type_code") or None,
                price_type_code=first_price_type,
                delivery_address=raw.get("delivery_address_full") or raw.get("delivery_address_short") or None,
                delivery_number=raw.get("delivery_number") or None,
                contract_number=raw.get("contract_number") or None,
                note=raw.get("note") or raw.get("deal_note") or None,
                discount_value=_f(raw.get("deal_margin_value")),
                discount_kind=raw.get("deal_margin_kind") or None,
                weight_netto=_f(raw.get("total_weight_netto")),
                weight_brutto=_f(raw.get("total_weight_brutto")),
                litre=_f(raw.get("total_litre")),
                sales_manager_name=raw.get("sales_manager_name") or None,
                expeditor_name=raw.get("expeditor_name") or None,
                driver_name=raw.get("driver_name") or None,
                self_shipment=raw.get("self_shipment") or None,
                lines=lines,
            ))
        return orders

    async def attach_marking_codes(self, deal_id: str, products: list[dict]) -> bool:
        """POST mdeal/order$import_order_marking_codes
        products: [{"product_unit_id": "...", "marking_codes": ["KIZ1", ...]}]"""
        data = await self._post(
            "b/anor/mxsx/mdeal/order$import_order_marking_codes",
            {"deal_id": deal_id, "products": products},
        )
        return data.get("success", True)

    async def change_order_status(self, deal_id: str, new_status: str) -> bool:
        data = await self._post(
            "b/trade/txs/tdeal/order$change_status",
            {"order": [{"deal_id": deal_id, "status": new_status}]},
        )
        return data.get("success", True)

    # ── Inventory balance (svereka) ───────────────────────────────────────────
    async def get_inventory_balance(
        self,
        warehouse_codes: list[str],
        begin_date: str,
        end_date: str,
        filial_code: str | None = None,
        product_conditions: list[str] | None = None,  # F / B / T
    ) -> list[dict]:
        body: dict[str, Any] = {
            "begin_date": begin_date,
            "end_date": end_date,
        }
        # Sklad kodi berilgan bo'lsagina filtrlaymiz; aks holda butun filial qoldig'i.
        if warehouse_codes:
            body["warehouse_codes"] = [{"warehouse_code": c} for c in warehouse_codes]
        # filial_code MAJBURIY (balance$export) — berilmasa connector'dagi default.
        fc = filial_code or self.filial_code
        if fc:
            body["filial_code"] = fc
        if product_conditions:
            body["product_conditions"] = product_conditions
        data = await self._post("b/anor/mxsx/mkw/balance$export", body)
        return data.get("balance", [])

    # ── Production receipts (zavod kirimi) ────────────────────────────────────
    async def get_inputs(
        self,
        warehouse_codes: list[str] | None = None,
        begin_modified_on: str | None = None,
        end_modified_on: str | None = None,
    ) -> list[dict]:
        body: dict[str, Any] = {}
        # Kirim TASHKILOT (filial) darajasida — sklad kodi filial EMAS.
        if self.filial_code:
            body["filial_code"] = self.filial_code
        if begin_modified_on:
            body["begin_modified_on"] = begin_modified_on
        if end_modified_on:
            body["end_modified_on"] = end_modified_on
        data = await self._post("b/anor/mxsx/mkw/input$export", body)
        return data.get("input", [])

    # ── Warehouse exports (pull) ──────────────────────────────────────────────
    async def get_movements(
        self, warehouse_codes: list[str] | None = None,
        begin_modified_on: str | None = None, end_modified_on: str | None = None,
    ) -> list[dict]:
        """Ichki ko'chirishlar (sklad↔sklad). mkw/movement$export"""
        return await self._export(
            "b/anor/mxsx/mkw/movement$export", "movement",
            warehouse_codes=warehouse_codes,
            begin_modified_on=begin_modified_on, end_modified_on=end_modified_on,
        )

    async def get_cross_org_movements(
        self, warehouse_codes: list[str] | None = None,
        begin_modified_on: str | None = None, end_modified_on: str | None = None,
    ) -> list[dict]:
        """Tashkilotlararo ko'chirishlar. mfm/movement$export"""
        return await self._export(
            "b/anor/mxsx/mfm/movement$export", "movement",
            warehouse_codes=warehouse_codes,
            begin_modified_on=begin_modified_on, end_modified_on=end_modified_on,
        )

    async def get_stocktakings(
        self, warehouse_codes: list[str] | None = None,
        begin_modified_on: str | None = None, end_modified_on: str | None = None,
    ) -> list[dict]:
        """Inventarizatsiyalar. mkw/stocktaking$export"""
        return await self._export(
            "b/anor/mxsx/mkw/stocktaking$export", "stocktaking",
            warehouse_codes=warehouse_codes,
            begin_modified_on=begin_modified_on, end_modified_on=end_modified_on,
        )

    async def get_writeoffs(
        self, warehouse_codes: list[str] | None = None,
        begin_modified_on: str | None = None, end_modified_on: str | None = None,
    ) -> list[dict]:
        """Spisaniyelar. mkw/writeoff$export"""
        return await self._export(
            "b/anor/mxsx/mkw/writeoff$export", "writeoff",
            warehouse_codes=warehouse_codes,
            begin_modified_on=begin_modified_on, end_modified_on=end_modified_on,
        )

    async def get_supplier_returns(
        self, warehouse_codes: list[str] | None = None,
        begin_modified_on: str | None = None, end_modified_on: str | None = None,
    ) -> list[dict]:
        """Postavshchikka qaytarishlar. mkw/return$export"""
        return await self._export(
            "b/anor/mxsx/mkw/return$export", "return",
            warehouse_codes=warehouse_codes,
            begin_modified_on=begin_modified_on, end_modified_on=end_modified_on,
        )

    async def get_purchases(
        self, warehouse_codes: list[str] | None = None,
        begin_modified_on: str | None = None, end_modified_on: str | None = None,
    ) -> list[dict]:
        """Xaridlar. mkw/purchase$export"""
        return await self._export(
            "b/anor/mxsx/mkw/purchase$export", "purchase",
            warehouse_codes=warehouse_codes,
            begin_modified_on=begin_modified_on, end_modified_on=end_modified_on,
        )

    async def get_sale_returns(
        self, warehouse_codes: list[str] | None = None,
        begin_modified_on: str | None = None, end_modified_on: str | None = None,
    ) -> list[dict]:
        """Sotuvdan qaytarishlar (mijozdan). mdeal/return$export"""
        return await self._export(
            "b/anor/mxsx/mdeal/return$export", "return",
            warehouse_codes=warehouse_codes,
            begin_modified_on=begin_modified_on, end_modified_on=end_modified_on,
        )

    # ── Postings (import) ──────────────────────────────────────────────────────
    async def post_movement(self, payload: dict) -> bool:
        data = await self._post("b/anor/mxsx/mkw/movement$import", payload)
        return data.get("success", True)

    async def post_stocktaking(self, payload: dict) -> bool:
        data = await self._post("b/anor/mxsx/mkw/stocktaking$import", payload)
        return data.get("success", True)

    async def post_writeoff(self, payload: dict) -> bool:
        data = await self._post("b/anor/mxsx/mkw/writeoff$import", payload)
        return data.get("success", True)

    async def post_cross_org_movement(self, payload: dict) -> bool:
        """Tashkilotlararo ko'chirish import. mfm/movement$import"""
        data = await self._post("b/anor/mxsx/mfm/movement$import", payload)
        return data.get("success", True)

    async def change_cross_org_movement_status(self, movement_id: str, status: str) -> bool:
        """mfm/movement$change_status"""
        data = await self._post(
            "b/anor/mxsx/mfm/movement$change_status",
            {"movement": [{"movement_id": movement_id, "status": status}]},
        )
        return data.get("success", True)

    async def post_supplier_return(self, payload: dict) -> bool:
        """Postavshchikka qaytarish import. mkw/return$import"""
        data = await self._post("b/anor/mxsx/mkw/return$import", payload)
        return data.get("success", True)

    # ── References (master data) ──────────────────────────────────────────────
    async def get_product_references(
        self,
        code: str | None = None,
        begin_modified_on: str | None = None,
        end_modified_on: str | None = None,
    ) -> list[dict]:
        body: dict[str, Any] = {}
        if code:
            body["code"] = code
        if begin_modified_on:
            body["begin_modified_on"] = begin_modified_on
        if end_modified_on:
            body["end_modified_on"] = end_modified_on
        data = await self._post("b/anor/mxsx/mr/inventory$export", body)
        return data.get("inventory", [])
