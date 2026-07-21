"""
Asl Belgisi (xtrace) connector — OPEN API v1.28.0.

Base URL: https://xtrace.aslbelgisi.uz  (stage: https://xtrace.stage.aslbelgisi.uz)
Auth: Business User apiKey → Authorization: Bearer <apiKey>

Rate limits (per docs §1.4):
  - owner-check / validate:  ≤10 req/s/user, ≤100 codes/req (owner-check), ≤1000 (validate)
  - Orders & Reports:        100/min
  - aggregation capacity:    GROUP=200, BOX_LV_1=1500, BOX_LV_2=500, SET=200
  - min code length 20; Cyrillic rejected; MC keeps ASCII GS () separators
"""
from __future__ import annotations

import asyncio
import base64
import json
from dataclasses import dataclass, field
from typing import Any

import httpx
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from app.core.circuit import CircuitBreaker, get_breaker
from app.core.config import settings


def _is_transient(exc: BaseException) -> bool:
    """Faqat o'tkinchi xatolarda qayta urinish: tarmoq, 5xx, 429.
    4xx (404/400 — masalan GTIN yo'q) darhol qaytariladi, qayta urinilmaydi."""
    if isinstance(exc, httpx.TransportError):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        code = exc.response.status_code
        return code >= 500 or code == 429
    return False


# reraise=True — tenacity asl xatoni (HTTPStatusError) qaytaradi, RetryError ichiga
# o'ramaydi; shunda chaqiruvchilardagi `except httpx.HTTPStatusError` ishlaydi.
_RETRY = dict(
    retry=retry_if_exception(_is_transient),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    reraise=True,
)


# ── owner-check result types (real API shape) ────────────────────────────────
# Parent kodni xom javobdan topish uchun maydonlar (Buxgalteriya Ocard bilan bir xil).
_PARENT_FIELDS = (
    "parentCode", "aggregateCode", "parentIdentifier", "parentId", "parentUnit",
    "containerCode", "aggregationCode", "packCode", "boxCode", "palletCode",
    "groupCode", "sscc",
)


def _extract_parent(item: dict) -> str | None:
    """Xom owner-check/private item'idan parent (yuqori agregat) kodni topadi."""
    for f in _PARENT_FIELDS:
        v = item.get(f)
        if isinstance(v, str) and len(v) >= 10:
            return v
    for ns in ("packageData", "codeData", "markingData", "productData"):
        sub = item.get(ns)
        if isinstance(sub, dict):
            for f in _PARENT_FIELDS:
                v = sub.get(f)
                if isinstance(v, str) and len(v) >= 10:
                    return v
    return None


@dataclass
class OwnerCheckCode:
    """One code returned by nested-codes/owner-check."""
    code: str
    package_type: str                       # UNIT/GROUP/BOX_LV_1/BOX_LV_2/ACC/SET
    status: str | None = None               # APPLIED/INTRODUCED/…
    extended_status: str | None = None
    product_group_id: int | None = None
    issuer_tin: str | None = None
    parent: str | None = None               # yuqori agregat kod (tepaga qidirish uchun)
    children: list[str] = field(default_factory=list)  # immediate child code STRINGS


@dataclass
class OwnerCheckResponse:
    codes: list[OwnerCheckCode] = field(default_factory=list)
    forbidden_codes: list[str] = field(default_factory=list)  # owned by another TIN
    missing_codes: list[str] = field(default_factory=list)    # not found in system

    def by_code(self) -> dict[str, OwnerCheckCode]:
        return {c.code: c for c in self.codes}

    def is_owned(self, code: str) -> bool:
        return code not in self.forbidden_codes and code not in self.missing_codes


@dataclass
class PrivateCode:
    """Detailed per-code info from cod/private/codes (gtin, batch, dates)."""
    code: str
    gtin: str | None = None
    package_type: str | None = None
    expiry_date: str | None = None
    production_date: str | None = None
    series_number: str | None = None
    status: str | None = None
    raw: dict = field(default_factory=dict)


class AslBelgisiClient:
    """Async client for the Asl Belgisi xtrace OPEN API."""

    def __init__(
        self,
        api_key: str,
        base_url: str = "",
        tin: str = "",
        business_place_id: int | str | None = None,
    ) -> None:
        self._base_url = (base_url or settings.ASLBELGISI_BASE_URL).rstrip("/")
        self.tin = tin
        self.business_place_id = business_place_id
        self._headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    # ── Internal helpers ────────────────────────────────────────────────────
    @property
    def _breaker(self) -> CircuitBreaker:
        return get_breaker(f"aslbelgisi:{self._base_url}")

    @retry(**_RETRY)
    async def _post_raw(self, path: str, payload: dict) -> Any:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{self._base_url}/{path.lstrip('/')}", json=payload, headers=self._headers
            )
            resp.raise_for_status()
            return resp.json()

    @retry(**_RETRY)
    async def _get_raw(self, path: str, params: dict | None = None) -> Any:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{self._base_url}/{path.lstrip('/')}", params=params, headers=self._headers
            )
            resp.raise_for_status()
            return resp.json()

    async def _post(self, path: str, payload: dict) -> Any:
        # Retry ichkarida (o'tkinchi xatolar), circuit tashqarida (to'liq
        # muvaffaqiyatsiz operatsiya = 1 xato). 4xx (owner logikasi) circuit'ni
        # ochmaydi — u ishlamay qolish emas; faqat o'tkinchi/5xx sanaladi.
        br = self._breaker
        br.before_call()
        try:
            data = await self._post_raw(path, payload)
        except httpx.HTTPStatusError as exc:
            if _is_transient(exc):
                br.on_failure()
            else:
                br.on_success()
            raise
        except Exception:
            br.on_failure()
            raise
        br.on_success()
        return data

    async def _get(self, path: str, params: dict | None = None) -> Any:
        br = self._breaker
        br.before_call()
        try:
            data = await self._get_raw(path, params)
        except httpx.HTTPStatusError as exc:
            if _is_transient(exc):
                br.on_failure()
            else:
                br.on_success()
            raise
        except Exception:
            br.on_failure()
            raise
        br.on_success()
        return data

    # ── Auth / key ──────────────────────────────────────────────────────────
    async def check_api_key(self) -> dict[str, Any]:
        return await self._get(f"public/api/v1/party/parties/{self.tin}/api-keys/check")

    async def refresh_api_key(self) -> str:
        data = await self._post(
            f"public/api/v1/party/parties/{self.tin}/api-keys/refresh", {"tin": self.tin}
        )
        return data["apiKey"]

    # ── Product registry (mahsulot kartochkasi) ───────────────────────────────
    async def search_product_by_gtin(self, gtin: str, limit: int = 5) -> list[dict]:
        """Asl Belgisi mahsulot-reyestri — GTIN bo'yicha kartochka(lar).
        Javob: {hasNextPage, products:[{name{uz,ru,en}, status, packageType,
        tnved, producer, unit, files/images ...}]}."""
        data = await self._get(
            "public/api/v1/product-registry/product/search-by-gtin",
            params={"gtin": gtin, "limit": limit, "offset": 0},
        )
        if isinstance(data, dict):
            return data.get("products", []) or []
        return data or []

    async def get_product_detail(self, product_id: str) -> dict:
        """Mahsulotning to'liq ma'lumoti (attributes + fotosuratlar)."""
        return await self._get(f"public/api/v1/product-registry/product/{product_id}")

    def photo_files(self, detail: dict) -> list[str]:
        """Detail attributes'dan barcha mahsulot foto fileName'lari (tartiblangan:
        front_side birinchi). Endpoint har birini navbatma-navbat sinaydi."""
        attrs = detail.get("attributes") if isinstance(detail, dict) else None
        if not isinstance(attrs, list):
            return []
        order = ["front_side", "upper_side", "left_side", "right_side", "back_side", "down_side", "other"]
        photos: dict[str, list[str]] = {}
        for a in attrs:
            meta = a.get("meta") or {}
            if meta.get("type") != "FILE_LIST":
                continue
            files = ((a.get("value") or {}).get("files")) or []
            names = [f.get("fileName") for f in files if f.get("fileName")]
            if names:
                photos.setdefault(meta.get("code") or "", []).extend(names)
        out: list[str] = []
        for code in order:
            out += photos.get(code, [])
        for code, names in photos.items():
            if code not in order:
                out += names
        return out

    async def get_product_file_b64(self, file_id: str) -> tuple[str, str] | None:
        """Mahsulot rasmini (base64, mime) qaytaradi — data-URI uchun."""
        import base64 as _b64
        fid = (file_id or "").strip()
        # Endpoint {id} sof UUID kutadi — kengaytmani (.jpg) olib tashlaymiz.
        if "." in fid:
            fid = fid.rsplit(".", 1)[0]
        if not fid:
            return None
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{self._base_url}/public/api/v1/product-registry/file/{fid}",
                headers={"Authorization": self._headers.get("Authorization", ""),
                         "Accept": "image/*, application/octet-stream, */*"},
            )
            resp.raise_for_status()
            mime = resp.headers.get("content-type", "image/jpeg").split(";")[0]
            return _b64.b64encode(resp.content).decode(), mime

    # ── Codes (read) ─────────────────────────────────────────────────────────
    async def owner_check(self, codes: list[str], tin: str | None = None) -> OwnerCheckResponse:
        """
        Ownership check + immediate nested children for transport/aggregate codes.
        Splits into ≤100-code chunks and throttles to stay under 10 req/s.
        """
        owner_tin = tin or self.tin
        merged = OwnerCheckResponse()
        chunks = [codes[i : i + 100] for i in range(0, len(codes), 100)]
        for idx, chunk in enumerate(chunks):
            data = await self._post(
                "public/api/cod/nested-codes/owner-check",
                {"codes": chunk, "ownerTin": owner_tin},
            )
            for item in data.get("results", []):
                issuer = item.get("issuerShortInfo") or {}
                merged.codes.append(
                    OwnerCheckCode(
                        code=item.get("code", ""),
                        package_type=item.get("packageType", "UNIT"),
                        status=item.get("status"),
                        extended_status=item.get("extendedStatus"),
                        product_group_id=item.get("productGroupId"),
                        issuer_tin=issuer.get("issuerTin"),
                        parent=_extract_parent(item),
                        children=list(item.get("children", []) or []),
                    )
                )
            merged.forbidden_codes.extend(data.get("forbiddenCodes", []) or [])
            merged.missing_codes.extend(data.get("missingCodes", []) or [])
            if idx < len(chunks) - 1:
                await asyncio.sleep(0.12)
        return merged

    async def private_codes(self, codes: list[str]) -> list[PrivateCode]:
        """Detailed info (GTIN, batch, expiry, production date) for codes."""
        out: list[PrivateCode] = []
        chunks = [codes[i : i + 100] for i in range(0, len(codes), 100)]
        for idx, chunk in enumerate(chunks):
            data = await self._post("public/api/cod/private/codes", {"codes": chunk})
            for item in data.get("results", data.get("codes", [])):
                out.append(
                    PrivateCode(
                        code=item.get("code", ""),
                        gtin=item.get("gtin"),
                        package_type=item.get("packageType"),
                        expiry_date=item.get("expirationDate") or item.get("expiryDate"),
                        production_date=item.get("productionDate"),
                        series_number=item.get("seriesNumber"),
                        status=item.get("status"),
                        raw=item,
                    )
                )
            if idx < len(chunks) - 1:
                await asyncio.sleep(0.12)
        return out

    async def verify_codes(self, codes: list[str]) -> list[dict]:
        """Validate an array of full marking codes (≤1000)."""
        return await self._post("public/api/v1/code-verification/verify", {"codes": codes})

    # Mahsulot guruhlari (Buxgalteriya Ocard bilan bir xil)
    PRODUCT_GROUPS = [
        "water", "alcohol", "beer", "pharma", "perfumery",
        "shoes", "linen", "milk", "tobacco",
    ]

    async def list_products(self, product_group: str) -> list[dict]:
        """product-registry dan bitta guruh bo'yicha mahsulotlar ro'yxati."""
        try:
            data = await self._get(
                "public/api/v1/product-registry/product",
                {"productGroup": product_group},
            )
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code in (400, 404):
                return []
            raise
        if isinstance(data, dict):
            return data.get("products", [])
        return data if isinstance(data, list) else []

    async def product_by_gtin(self, gtin: str) -> dict | None:
        """Find a product description by GTIN (returns first match or None)."""
        try:
            data = await self._get(
                "public/api/v1/product-registry/product/search-by-gtin", {"gtin": gtin}
            )
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                return None
            raise
        products = data.get("products", [])
        return products[0] if products else None

    # ── Documents (write) ────────────────────────────────────────────────────
    def _document_body(self, body: dict, *, sort_keys: bool = False) -> str:
        payload = json.dumps(body, separators=(",", ":"), sort_keys=sort_keys, ensure_ascii=False)
        return base64.b64encode(payload.encode("utf-8")).decode("ascii")

    async def send_aggregation(self, body: dict, signature: str | None = None) -> str:
        """doc/aggregation — body is the JSON structure (will be base64-wrapped)."""
        wrap: dict[str, Any] = {"documentBody": self._document_body(body)}
        if signature:
            wrap["signature"] = signature
        data = await self._post("public/api/v1/doc/aggregation", wrap)
        return data["documentId"]

    async def send_disaggregation(self, body: dict, signature: str | None = None) -> str:
        """doc/transport-code-disaggregation — JSON keys sorted A–Z before base64."""
        wrap: dict[str, Any] = {"documentBody": self._document_body(body, sort_keys=True)}
        if signature:
            wrap["signature"] = signature
        data = await self._post("public/api/v1/doc/transport-code-disaggregation", wrap)
        return data["documentId"]

    # ── Documents (status / async polling) ────────────────────────────────────
    async def get_doc(self, document_id: str) -> dict:
        return await self._get(f"public/api/v1/doc/storage/docs/{document_id}")

    async def get_doc_codes(self, document_id: str, limit: int = 30000) -> list[dict]:
        """Per-code processing status: SUCCESS/WARNING/ERROR (+ reason)."""
        return await self._get(
            f"public/api/v1/doc/storage/docs/{document_id}/codes", {"limit": limit}
        )

    async def get_doc_errors(self, document_id: str) -> dict:
        return await self._get(f"public/api/v1/doc/storage/errors/{document_id}")
