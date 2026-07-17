"""
Label service (TZ §7.12).

Pure functions that build Zebra ZPL II strings for thermal label printers.
No DB / IO here — endpoints load the data and pass plain values in.

ZPL primer (what we use):
  ^XA          start of label
  ^CI28        UTF-8 input encoding (so human-readable text isn't mangled)
  ^FOx,y       field origin (dots from top-left); ~8 dots per mm at 203dpi
  ^A0N,h,w     scalable font 0, normal orientation, height/width in dots
  ^BY w,r,h    barcode defaults: module width, ratio, height
  ^BCN,h,Y,N,N Code128, normal orientation, height, print interpretation line
  ^FD ... ^FS  field data ... field separator (end of field)
  ^XZ          end of label

Labels are sized for a common 4"x2" (~812x406 dots @ 203dpi) stock but the
content is anchored top-left, so smaller stock still prints the essentials.
"""
from __future__ import annotations


def _zpl_escape(text: str) -> str:
    """Escape characters that are special inside a ^FD field.

    ^ and ~ are ZPL control prefixes; \\ is the hex-escape introducer.
    Replacing them with a space keeps the label valid and readable.
    """
    if text is None:
        return ""
    return str(text).replace("\\", " ").replace("^", " ").replace("~", " ")


def location_label_zpl(code: str, barcode: str | None, human: str) -> str:
    """Storage-location label: Code128 barcode + large human-readable code.

    Args:
        code:    location code (e.g. "A-01-03-02"), used as barcode fallback.
        barcode: explicit barcode payload if the location has one.
        human:   big readable line (usually the code, possibly zone-prefixed).
    """
    data = (barcode or code or "").strip()
    big = _zpl_escape(human or code)
    sub = _zpl_escape(code)
    return (
        "^XA"
        "^CI28"
        "^PW812"
        "^LH0,0"
        # Big human-readable line at top
        f"^FO40,30^A0N,80,80^FD{big}^FS"
        # Code128 barcode (with its own interpretation line)
        "^BY3,2,140"
        f"^FO40,140^BCN,140,Y,N,N^FD{_zpl_escape(data)}^FS"
        # Small caption underneath
        f"^FO40,320^A0N,30,30^FDLocation: {sub}^FS"
        "^XZ"
    )


def pallet_label_zpl(sscc: str, product_name: str, qty: int, batch: str | None) -> str:
    """Pallet / aggregate (SSCC) label: Code128 of SSCC + product details.

    Args:
        sscc:         SSCC / aggregation marking code (barcode payload).
        product_name: product display name.
        qty:          units on the pallet.
        batch:        lot / batch number, optional.
    """
    name = _zpl_escape(product_name)
    code = _zpl_escape((sscc or "").strip())
    batch_line = f"Batch: {_zpl_escape(batch)}" if batch else "Batch: -"
    return (
        "^XA"
        "^CI28"
        "^PW812"
        "^LH0,0"
        # Product name (top, may be long)
        f"^FO40,30^A0N,55,55^FD{name}^FS"
        # SSCC barcode
        "^BY3,2,150"
        f"^FO40,110^BCN,150,Y,N,N^FD{code}^FS"
        # Qty + batch caption row
        f"^FO40,300^A0N,40,40^FDQty: {int(qty)}^FS"
        f"^FO320,300^A0N,40,40^FD{batch_line}^FS"
        "^XZ"
    )
