import sys
import tkinter as tk
from tkinter import messagebox, scrolledtext
import json
import requests
import re
import base64
from datetime import datetime


# --- Aggregation API (existing flow) ---
API_URL = "https://xtrace.aslbelgisi.uz/public/api/v1/doc/aggregation"
API_KEY = "29510cc0-0597-423b-92a8-849c4e7ac581"
TIMEOUT = 15

BUSINESS_PLACE_ID = 6273
PRODUCTION_ORDER_ID = "2"
AGGREGATION_UNIT_CAPACITY = 10
SHOULD_BE_UNBUNDLED = True


# --- Code info API (OpenAPI v1.23.0 9.1/9.2) ---
COD_API_BASE = "https://xtrace.aslbelgisi.uz"
COD_PRIVATE_CODES_PATH = "/public/api/cod/private/codes"
COD_PUBLIC_CODES_PATH = "/public/api/cod/public/codes"


root = None
input_box = None
homogeneous_var = None


def _api_child_code(code: str) -> str:
    c = re.sub(r"\s+", "", code)
    if len(c) >= 31:
        return c[:31]
    return c


def _is_unit_0104(code: str) -> bool:
    return code.startswith("0104")


def _is_box_01x4(code: str) -> bool:
    return len(code) >= 4 and code.startswith("01") and code[2].isdigit() and code[2] != "0" and code[3] == "4"


def line_duplicate_key(line: str):
    if not line.strip():
        return None
    compact = re.sub(r"\s+", "", line)
    if compact.isdigit() and len(compact) >= 10:
        return compact
    if compact.startswith(("00", "01")):
        code = compact
    else:
        m = re.search(r"(00|01)[A-Za-z0-9]+", compact)
        code = m.group(0) if m else compact
    if code.startswith("01") and len(code) >= 31:
        return code[:31]
    return code


def dedupe_input_text(text: str) -> str:
    lines = text.splitlines()
    seen = set()
    out = []
    for line in lines:
        key = line_duplicate_key(line)
        if key is None:
            out.append(line)
            continue
        if key in seen:
            continue
        seen.add(key)
        out.append(line)
    return "\n".join(out)


def dedupe_scrolled_text(widget):
    t = widget.get("1.0", "end-1c")
    new = dedupe_input_text(t)
    if new != t:
        widget.delete("1.0", tk.END)
        widget.insert("1.0", new)


def _parse_homogeneous_digit_block(compacts: list[str]):
    if len(compacts) < 2:
        return None
    L = len(compacts[0])
    if L < 10:
        return None
    for c in compacts:
        if not c.isdigit() or len(c) != L:
            return None
    return [
        {
            "parent": compacts[0],
            "children": [_api_child_code(x) for x in compacts[1:]],
        }
    ], []


def parse_input(text: str, homogeneous_digit_block: bool = True):
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    compacts = [re.sub(r"\s+", "", line) for line in lines]

    if homogeneous_digit_block:
        hom = _parse_homogeneous_digit_block(compacts)
        if hom is not None:
            return hom

    groups = []
    current = None
    invalid_lines = []

    for line in lines:
        compact = re.sub(r"\s+", "", line)

        if compact.startswith(("00", "01")):
            code = compact
        else:
            m = re.search(r"(00|01)[A-Za-z0-9]+", compact)
            if not m:
                invalid_lines.append(line)
                continue
            code = m.group(0)

        if code.startswith("00") or _is_box_01x4(code):
            if current is not None:
                groups.append(current)
            current = {"parent": code, "children": []}
        elif code.startswith("01"):
            if current is None:
                raise ValueError(f"Child kodi (01...) parentdan oldin keldi: {line}")
            if not _is_unit_0104(code):
                invalid_lines.append(f"{line}  (faqat 0104... unit child qabul qilinadi)")
                continue
            if len(code) < 31:
                invalid_lines.append(f"{line}  (child uzunligi {len(code)} < 31)")
                continue
            current["children"].append(_api_child_code(code))
        else:
            invalid_lines.append(line)
            continue

    if current is not None:
        groups.append(current)

    if not groups:
        raise ValueError("Hech bo'lmaganda bitta parent kod topilmadi.")

    return groups, invalid_lines


def normalize_parent_code(parent: str) -> str:
    c = re.sub(r"\s+", "", parent)
    if c.startswith(("00", "01")):
        return c
    return "00" + c


def build_payload(groups):
    aggregation_units = []
    for g in groups:
        items_count = len(g["children"])
        aggregation_units.append(
            {
                "aggregationItemsCount": items_count,
                "aggregationUnitCapacity": items_count,
                "codes": g["children"],
                "shouldBeUnbundled": SHOULD_BE_UNBUNDLED,
                "unitSerialNumber": normalize_parent_code(g["parent"]),
            }
        )

    document_body_obj = {
        "aggregationUnits": aggregation_units,
        "businessPlaceId": BUSINESS_PLACE_ID,
        "documentDate": datetime.now().astimezone().isoformat(timespec="seconds"),
        "productionOrderId": PRODUCTION_ORDER_ID,
    }

    raw = json.dumps(document_body_obj, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    document_body_b64 = base64.b64encode(raw).decode("ascii")
    return {"documentBody": document_body_b64}


def send_to_asl_belgisi(payload):
    headers = {
        "Content-Type": "application/json;charset=UTF-8",
        "Authorization": f"Bearer {API_KEY}",
    }
    response = requests.request(
        "POST",
        API_URL,
        headers=headers,
        json=payload,
        timeout=TIMEOUT,
    )

    if 200 <= response.status_code < 300:
        return True, response.text

    allow = response.headers.get("Allow")
    content_type = response.headers.get("Content-Type")
    details = [
        "Method: POST",
        f"URL: {API_URL}",
        f"Status: {response.status_code}",
    ]
    if allow:
        details.append(f"Allow: {allow}")
    if content_type:
        details.append(f"Content-Type: {content_type}")
    return False, "\n".join(details) + "\n\nBody:\n" + (response.text or "")


def _extract_candidate_codes(text: str) -> list[str]:
    """
    Input_box dagi satrlardan kodlarni ajratib oladi.
    - Agar satr 00/01 bilan boshlansa, o'shani oladi.
    - Aks holda satr ichidan (00|01) bilan boshlanuvchi tokenni qidiradi.
    """
    out = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        compact = re.sub(r"\s+", "", line)
        if compact.startswith(("00", "01")):
            out.append(compact)
            continue
        m = re.search(r"(00|01)[A-Za-z0-9]+", compact)
        if m:
            out.append(m.group(0))
    return out


def _strip_crypto_tail(code: str) -> str:
    """
    "Crypto Tail" (tekshiruv kodi) qismini olib tashlaydi va faqat Identification Code qoldiradi.
    Amaliy qoida:
    - 01... kodlar uchun identifikatsiya qismi 31 belgigacha.
    - Boshqa holatlarda (00...) kodlar o'zgarmaydi (agar tail mavjud bo'lsa ham, API odatda uni e'tiborsiz qoldiradi).
    """
    c = re.sub(r"\s+", "", code)
    if c.startswith("01") and len(c) > 31:
        return c[:31]
    return c


def _cod_headers():
    return {
        "Content-Type": "application/json;charset=UTF-8",
        "Authorization": f"Bearer {API_KEY}",
    }


def _post_codes(path: str, codes: list[str]):
    url = COD_API_BASE + path
    payload = {"codes": codes, "addCodeHistory": True}
    resp = requests.post(url, headers=_cod_headers(), json=payload, timeout=TIMEOUT)
    return resp


def _json_safe(resp):
    try:
        return resp.json()
    except Exception:
        return None


def _format_info_items(data) -> list[dict]:
    """
    Har xil response formatlariga moslashish uchun "items" ni ajratib beradi.
    Kutiladigan variantlar:
    - {"results":[...], "forbiddenCodes":[...]} (hujjatdagi namuna)
    - {"codes":[...], "forbiddenCodes":[...]} yoki {"items":[...]} yoki bevosita [...]
    """
    if data is None:
        return []
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for k in ("results", "codes", "items", "data", "result"):
            v = data.get(k)
            if isinstance(v, list):
                return v
    return []


def _get_forbidden_codes(data) -> list[str]:
    if not isinstance(data, dict):
        return []
    fc = data.get("forbiddenCodes")
    if isinstance(fc, list):
        return [str(x) for x in fc if str(x).strip()]
    return []


def _pick_field(obj: dict, keys: list[str]):
    for k in keys:
        if k in obj and obj.get(k) not in (None, ""):
            return obj.get(k)
    lower_map = {str(k).lower(): k for k in obj.keys()}
    for k in keys:
        real = lower_map.get(k.lower())
        if real is not None and obj.get(real) not in (None, ""):
            return obj.get(real)
    return None


def _normalize_date(v):
    if v is None:
        return ""
    if isinstance(v, str):
        return v
    return str(v)


def _get_nested(obj, path: list[str]):
    cur = obj
    for key in path:
        if not isinstance(cur, dict) or key not in cur:
            return None
        cur = cur.get(key)
    return cur


def _chunk_list(items: list[str], size: int) -> list[list[str]]:
    if size <= 0:
        return [items]
    return [items[i : i + size] for i in range(0, len(items), size)]


def _entry_code(entry: dict) -> str | None:
    c = _get_nested(entry, ["codeData", "code"]) or _pick_field(entry, ["code"])
    return str(c) if c not in (None, "") else None


def _fetch_private_details(codes: list[str]) -> tuple[int, dict | None, str | None]:
    """
    Private API'dan codes bo'yicha ma'lumot olib keladi.
    Qaytaradi: (status_code, json_data, error_text)
    """
    resp = _post_codes(COD_PRIVATE_CODES_PATH, codes)
    if 200 <= resp.status_code < 300:
        return resp.status_code, _json_safe(resp), None
    return resp.status_code, None, resp.text or ""


def _build_code_index(results: list[dict]) -> dict[str, dict]:
    idx: dict[str, dict] = {}
    for e in results:
        if not isinstance(e, dict):
            continue
        c = _entry_code(e)
        if c:
            idx[c] = e
    return idx


def _collect_related_codes(results: list[dict]) -> set[str]:
    related: set[str] = set()
    for e in results:
        if not isinstance(e, dict):
            continue
        parent = _get_nested(e, ["packageData", "parentCode"])
        if parent:
            related.add(str(parent))
        children = _get_nested(e, ["packageData", "children"])
        if isinstance(children, list):
            for ch in children:
                if isinstance(ch, dict):
                    cc = ch.get("code")
                    if cc:
                        related.add(str(cc))
                elif isinstance(ch, str) and ch.strip():
                    related.add(ch.strip())
    return related


def _render_pretty_report(private_data, public_data, forbidden_codes: list[str], private_status: int, public_status: int | None):
    # Hujjatdagi namuna bo'yicha: {"results":[{codeData, packageData, turnoverData, productData, ...}], "forbiddenCodes":[...]}
    priv_results = _format_info_items(private_data)

    lines = []
    lines.append("ASL BELGISI — Code Info natijasi")
    lines.append("")
    lines.append(f"Private API status: {private_status}")
    if public_status is not None:
        lines.append(f"Public API status:  {public_status}")
    if forbidden_codes:
        lines.append(f"Forbidden codes: {len(forbidden_codes)} ta")
        lines.append("  " + ", ".join(forbidden_codes[:50]) + (" ..." if len(forbidden_codes) > 50 else ""))
    lines.append("")

    if not priv_results:
        lines.append("Natija: `results` bo'sh yoki response formati noma'lum.")
        return "\n".join(lines)

    # Indeks orqali parent/child/grandparent ko'rsatish uchun
    idx = _build_code_index(priv_results)

    def _child_list(entry: dict) -> list[dict]:
        ch = _get_nested(entry, ["packageData", "children"])
        if not isinstance(ch, list):
            return []
        out = []
        for item in ch:
            if isinstance(item, dict):
                out.append(item)
            elif isinstance(item, str) and item.strip():
                out.append({"code": item.strip()})
        return out

    def _parent_code(entry: dict) -> str | None:
        p = _get_nested(entry, ["packageData", "parentCode"])
        return str(p) if p not in (None, "") else None

    def _append_entry_block(entry: dict, title_prefix: str = "Code"):
        code = _get_nested(entry, ["codeData", "code"]) or _pick_field(entry, ["code"])
        status = _get_nested(entry, ["codeData", "status"]) or _pick_field(entry, ["status"])
        package_type = _get_nested(entry, ["packageData", "packageType"])
        parent_code = _parent_code(entry)
        actually_packed = _get_nested(entry, ["packageData", "actuallyPacked"])
        owner_tin = _get_nested(entry, ["turnoverData", "ownerInfo", "ownerTin"])
        prod_date = _get_nested(entry, ["productData", "productionDate"])
        emission_date = _get_nested(entry, ["markingData", "emissionDate"])
        issue_date = _get_nested(entry, ["markingData", "issueDate"])

        lines.append(f"{title_prefix}: {code if code is not None else ''}")
        lines.append("  Source: PRIVATE")
        lines.append(f"  Status: {status if status is not None else ''}")
        lines.append(f"  Package Type: {package_type if package_type is not None else ''}")
        if parent_code is not None:
            lines.append(f"  Parent Code: {parent_code}")
        if actually_packed is not None:
            lines.append(f"  Actually Packed: {actually_packed}")
        lines.append(f"  Owner TIN: {owner_tin if owner_tin is not None else ''}")

        prod_s = _normalize_date(prod_date)
        lines.append(f"  Production Date: {prod_s if prod_s else ''}")
        if not prod_s:
            if emission_date is not None:
                lines.append(f"  Emission Date: {_normalize_date(emission_date)}")
            if issue_date is not None:
                lines.append(f"  Issue Date: {_normalize_date(issue_date)}")

        children = _child_list(entry)
        if children:
            lines.append(f"  Children: {len(children)} ta")
            # ko'p bo'lsa ham, birinchi 50 tasini ko'rsatamiz
            for ch in children[:50]:
                cc = ch.get("code", "")
                cs = ch.get("status", "")
                cpt = ch.get("packageType", "")
                lines.append(f"    - {cc} | {cs} | {cpt}")
            if len(children) > 50:
                lines.append(f"    ... yana {len(children) - 50} ta")

    def _append_parent_chain(entry: dict):
        # parent -> grandparent (agar indexda bo'lsa)
        p = _parent_code(entry)
        if not p:
            return
        parent_entry = idx.get(p)
        if parent_entry:
            gp = _parent_code(parent_entry)
            if gp and gp in idx:
                lines.append("Grandparent:")
                _append_entry_block(idx[gp], title_prefix="  Code")
            lines.append("Parent:")
            _append_entry_block(parent_entry, title_prefix="  Code")

    # Asosiy natijalar: avval foydalanuvchi kiritgan kodlarga mos entrylar, qolganlarini oxirida.
    requested_set = set()
    if isinstance(private_data, dict):
        meta = private_data.get("meta")
        if isinstance(meta, dict):
            pass

    lines.append("-----")
    for entry in priv_results:
        if not isinstance(entry, dict):
            continue
        _append_parent_chain(entry)
        _append_entry_block(entry, title_prefix="Code")
        lines.append("-----")

    return "\n".join(lines)


def check_info_logic():
    dedupe_scrolled_text(input_box)
    raw_text = input_box.get("1.0", tk.END).strip()
    if not raw_text:
        messagebox.showwarning("Diqqat", "Kodlar maydoni bo'sh.")
        return

    raw_codes = _extract_candidate_codes(raw_text)
    if not raw_codes:
        messagebox.showwarning("Diqqat", "Kod topilmadi. (00... yoki 01... formatdagi kod kiriting)")
        return

    codes = []
    seen = set()
    for c in raw_codes:
        ident = _strip_crypto_tail(c)
        if ident and ident not in seen:
            seen.add(ident)
            codes.append(ident)

    if not codes:
        messagebox.showwarning("Diqqat", "Yuborish uchun kod qolmadi.")
        return

    private_data = None
    forbidden = []
    private_status = 0

    try:
        # 1) Asosiy so'rov (foydalanuvchi kiritgan kodlar)
        resp_priv = _post_codes(COD_PRIVATE_CODES_PATH, codes)
        private_status = resp_priv.status_code

        if resp_priv.status_code in (401, 403):
            body = resp_priv.text or ""
            messagebox.showerror(
                "Ruxsat yo'q",
                "Private API ruxsat bermadi (401/403).\n"
                "Bu rejimda faqat Private API ishlatiladi.\n\n"
                f"Status: {resp_priv.status_code}\n\n{body}",
            )
            return
        if not (200 <= resp_priv.status_code < 300):
            body = resp_priv.text or ""
            messagebox.showerror(
                "Xato",
                "Private API so'rovida xato:\n"
                f"Status: {resp_priv.status_code}\n\n"
                f"{body}",
            )
            return

        private_data = _json_safe(resp_priv)
        forbidden = _get_forbidden_codes(private_data)

        # 2) Ierarxiyani ko'rish uchun: child + parent (+ grandparent) kodlarini ham olib kelish
        base_results = _format_info_items(private_data)
        code_index = _build_code_index(base_results)

        MAX_DEPTH = 2  # parent + grandparent
        MAX_EXTRA_CODES = 400
        BATCH_SIZE = 100

        to_fetch = _collect_related_codes(base_results)
        to_fetch = {c for c in to_fetch if c and c not in code_index}
        fetched_total = 0

        depth = 0
        while to_fetch and depth < MAX_DEPTH and fetched_total < MAX_EXTRA_CODES:
            chunk_codes = list(to_fetch)[: min(BATCH_SIZE, MAX_EXTRA_CODES - fetched_total)]
            to_fetch = to_fetch.difference(chunk_codes)

            st, data2, err = _fetch_private_details(chunk_codes)
            if st in (401, 403):
                # Ruxsat bo'lmasa, chuqurlashtirishni to'xtatamiz — asosiy natijani ko'rsataveramiz
                break
            if not (200 <= st < 300) or data2 is None:
                # Xatoda ham asosiy natijani yo'qotmaymiz
                break

            res2 = _format_info_items(data2)
            for k, v in _build_code_index(res2).items():
                code_index.setdefault(k, v)

            fetched_total += len(chunk_codes)
            # Keyingi qatlam parent/child'larni ham qo'shamiz
            more = _collect_related_codes(res2)
            more = {c for c in more if c and c not in code_index}
            to_fetch |= more
            depth += 1

        # 3) Yig'ilgan natijani unified ko'rinishda report'ga uzatamiz
        private_data = {
            "results": list(code_index.values()),
            "forbiddenCodes": forbidden,
            "meta": {"expanded": True, "expandedDepth": depth, "expandedItems": len(code_index)},
        }
    except requests.RequestException as e:
        messagebox.showerror("Xato", f"API bilan ulanishda xato:\n{e}")
        return
    except Exception as e:
        messagebox.showerror("Xato", f"Check Info jarayonida xato:\n{e}")
        return

    report = _render_pretty_report(private_data, None, forbidden, private_status, None)

    win = tk.Toplevel(root)
    win.title("Check Info — Natijalar")
    win.geometry("900x600")

    out = scrolledtext.ScrolledText(win, width=110, height=35)
    out.pack(fill="both", expand=True, padx=10, pady=10)
    out.insert("1.0", report)
    out.configure(state="disabled")


def on_send():
    dedupe_scrolled_text(input_box)
    text = input_box.get("1.0", tk.END).strip()
    if not text:
        messagebox.showwarning("Diqqat", "Kodlar maydoni bo'sh.")
        return

    hom_mode = True if homogeneous_var is None else homogeneous_var.get()
    try:
        groups, invalid_lines = parse_input(text, homogeneous_digit_block=hom_mode)
    except Exception as e:
        messagebox.showerror("Xato", f"Kodlarni parse qilishda xato:\n{e}")
        return
    else:
        if invalid_lines:
            preview = "\n".join(invalid_lines[:10])
            more = ""
            if len(invalid_lines) > 10:
                more = f"\n... va yana {len(invalid_lines) - 10} ta satr"
            messagebox.showwarning(
                "Ogohlantirish",
                "Ba'zi satrlar 00/01 formatiga mos kelmadi va tashlab yuborildi:\n\n" f"{preview}{more}",
            )

    try:
        payload = build_payload(groups)
        success, info = send_to_asl_belgisi(payload)
        if success:
            doc_id = None
            try:
                data = json.loads(info) if info else {}
                if isinstance(data, dict):
                    doc_id = data.get("documentId")
            except Exception:
                pass

            if doc_id:
                messagebox.showinfo("Muvaffaqiyatli", f"Muvaffaqiyatli yuborildi.\nDocumentId: {doc_id}")
            else:
                messagebox.showinfo("Muvaffaqiyatli", "Muvaffaqiyatli yuborildi.")
        else:
            messagebox.showerror("Xato", f"Yuborishda xato:\n{info}")
    except Exception as e:
        messagebox.showerror("Xato", f"So'rov yuborishda xato:\n{e}")


def run_cli_test():
    c31 = "0123456789012345678901234567890"
    sample = f"""00PARENT_BOX_A
{c31}
{c31}
00PARENT_BOX_B
{c31}
"""
    groups, invalid_lines = parse_input(sample)
    print("=== CLI test: parse_input ===")
    for i, g in enumerate(groups):
        parent_out = normalize_parent_code(g["parent"])
        print(f"Guruh {i + 1}: unitSerialNumber={parent_out!r} (bolalar: {len(g['children'])})")
    if invalid_lines:
        print("Invalid:", invalid_lines)
    payload = build_payload(groups)
    raw = base64.b64decode(payload["documentBody"]).decode("utf-8")
    doc = json.loads(raw)
    print("\n=== documentBody (qisqa) ===")
    for u in doc.get("aggregationUnits", []):
        print("  unitSerialNumber:", u.get("unitSerialNumber"), "codes count:", len(u.get("codes", [])))


def main():
    global input_box, root, homogeneous_var
    root = tk.Tk()
    root.title("ASL BELGISI — Aggregation Sender + Check Info")

    label = tk.Label(root, text="Parent/Child kodlarini shu yerga joylashtiring:")
    label.pack(padx=10, pady=(10, 0))

    homogeneous_var = tk.BooleanVar(value=True)
    chk = tk.Checkbutton(
        root,
        text="Bir xil uzunlikdagi faqat raqamlar: 1-qator parent, qolganlari child",
        variable=homogeneous_var,
    )
    chk.pack(padx=10, pady=(0, 4), anchor="w")

    input_box = scrolledtext.ScrolledText(root, width=80, height=25)
    input_box.pack(padx=10, pady=10)

    def _dedupe_after_edit(_=None):
        root.after(1, lambda: dedupe_scrolled_text(input_box))

    input_box.bind("<<Paste>>", _dedupe_after_edit, add="+")
    input_box.bind("<Return>", _dedupe_after_edit, add="+")

    btn_row = tk.Frame(root)
    btn_row.pack(pady=(0, 12))

    send_button = tk.Button(btn_row, text="Send Aggregation", command=on_send, width=18)
    send_button.pack(side="left", padx=(0, 8))

    check_button = tk.Button(btn_row, text="Check Info", command=check_info_logic, width=12)
    check_button.pack(side="left")

    root.mainloop()


if __name__ == "__main__":
    if "--test" in sys.argv:
        run_cli_test()
    else:
        main()
