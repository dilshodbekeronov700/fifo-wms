import pytest

from app.services import putaway, sync


class _P:
    units_per_box = 8
    boxes_per_pallet = 25


def test_count_pallet_from_local_children():
    # Mahalliy hisoblash: box_count = bolalar soni, unit_count = box*units_per_box.
    rc = putaway.ResolvedCode(
        code="x", ownership_ok=True, package_type="BOX_LV_1",
        children=["a", "b", "c"],
    )
    rc.product = _P()
    putaway._compute_counts(rc)
    assert rc.box_count == 3
    assert rc.unit_count == 24
    assert rc.counting_method == "children"


def test_count_single_code_assumed():
    # Bolalarsiz kod = bitta qadoq (box) deb hisoblanadi.
    rc = putaway.ResolvedCode(code="u", ownership_ok=True, package_type="UNIT")
    putaway._compute_counts(rc)
    assert rc.box_count == 1
    assert rc.counting_method == "assumed_single"


def test_category_from_litr():
    assert sync._category_from_litr({"litr": "19"}) == "19L"
    assert sync._category_from_litr({"litr": "0.5"}) == "0.5L"
    assert sync._category_from_litr({"litr": ""}) is None
