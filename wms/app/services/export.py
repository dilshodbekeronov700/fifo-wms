"""
Export helpers (TZ §10) — pure, dependency-light serializers for tabular data.

CSV is always available (stdlib). Excel (openpyxl) and PDF (reportlab) are
optional: if the library is not importable we transparently fall back to CSV so
the API never hard-fails on a missing dependency.
"""
from __future__ import annotations

import csv
import io
from typing import Sequence


def _ordered_fields(rows: Sequence[dict]) -> list[str]:
    """Stable, union-of-keys column order (first-seen wins)."""
    fields: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for key in row.keys():
            if key not in seen:
                seen.add(key)
                fields.append(key)
    return fields


def _stringify(value: object) -> object:
    """Render non-primitive values into something a CSV/Excel cell can hold."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (str, int, float)):
        return value
    return str(value)


def to_csv(rows: list[dict], *, fieldnames: list[str] | None = None) -> str:
    """Serialize a list of dict rows to a CSV string (stdlib csv).

    Column order: explicit ``fieldnames`` if given, else union of keys in
    first-seen order. An empty ``rows`` (and no fieldnames) yields "".
    """
    cols = fieldnames if fieldnames is not None else _ordered_fields(rows)
    buf = io.StringIO()
    if not cols:
        return ""
    writer = csv.DictWriter(buf, fieldnames=cols, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow({c: _stringify(row.get(c)) for c in cols})
    return buf.getvalue()


def to_csv_bytes(rows: list[dict], *, fieldnames: list[str] | None = None) -> bytes:
    """UTF-8 (with BOM) encoded CSV — BOM makes Excel open it cleanly."""
    return b"\xef\xbb\xbf" + to_csv(rows, fieldnames=fieldnames).encode("utf-8")


def to_xlsx_bytes(
    rows: list[dict],
    *,
    fieldnames: list[str] | None = None,
    sheet_title: str = "Export",
) -> bytes | None:
    """Serialize to an .xlsx byte string. Returns None if openpyxl is absent."""
    try:
        from openpyxl import Workbook
    except ImportError:
        return None

    cols = fieldnames if fieldnames is not None else _ordered_fields(rows)
    wb = Workbook()
    ws = wb.active
    ws.title = sheet_title[:31] or "Export"
    if cols:
        ws.append(cols)
        for row in rows:
            ws.append([_stringify(row.get(c)) for c in cols])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def to_pdf_bytes(
    rows: list[dict],
    *,
    fieldnames: list[str] | None = None,
    title: str = "Export",
) -> bytes | None:
    """Serialize to a simple tabular PDF. Returns None if reportlab is absent."""
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import (
            SimpleDocTemplate,
            Table,
            TableStyle,
            Paragraph,
            Spacer,
        )
    except ImportError:
        return None

    cols = fieldnames if fieldnames is not None else _ordered_fields(rows)
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4))
    styles = getSampleStyleSheet()
    elements: list = [Paragraph(title, styles["Heading1"]), Spacer(1, 12)]

    if cols:
        data = [cols] + [[str(_stringify(r.get(c))) for c in cols] for r in rows]
        table = Table(data, repeatRows=1)
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTSIZE", (0, 0), (-1, -1), 7),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cbd5e1")),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ]
            )
        )
        elements.append(table)

    doc.build(elements)
    return buf.getvalue()


# --- format dispatch -------------------------------------------------------

# media type + filename extension per logical format
FORMAT_MEDIA = {
    "csv": ("text/csv; charset=utf-8", "csv"),
    "xlsx": (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "xlsx",
    ),
    "pdf": ("application/pdf", "pdf"),
}


def render(
    rows: list[dict],
    *,
    fmt: str,
    fieldnames: list[str] | None = None,
    title: str = "Export",
) -> tuple[bytes, str, str]:
    """Render rows in the requested format with graceful fallback to CSV.

    Returns (content_bytes, media_type, file_extension). If an optional format
    (xlsx/pdf) cannot be produced because its dependency is missing, falls back
    to CSV so the response is always valid.
    """
    fmt = (fmt or "csv").lower()
    if fmt == "xlsx":
        data = to_xlsx_bytes(rows, fieldnames=fieldnames, sheet_title=title)
        if data is not None:
            media, ext = FORMAT_MEDIA["xlsx"]
            return data, media, ext
    elif fmt == "pdf":
        data = to_pdf_bytes(rows, fieldnames=fieldnames, title=title)
        if data is not None:
            media, ext = FORMAT_MEDIA["pdf"]
            return data, media, ext

    media, ext = FORMAT_MEDIA["csv"]
    return to_csv_bytes(rows, fieldnames=fieldnames), media, ext
