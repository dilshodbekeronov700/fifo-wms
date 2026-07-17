import uuid

from app.models.inventory import AbcClass
from app.services import slotting


class _Zone:
    def __init__(self, rules):
        self.putaway_rules = rules


class _Product:
    id = uuid.uuid4()
    abc_class = AbcClass.A
    category = "19L"
    volume_m3 = 0.019


def test_zone_accepts_category_routing():
    p = _Product()
    assert slotting.zone_accepts(_Zone({"categories": ["19L"]}), p) is True
    assert slotting.zone_accepts(_Zone({"categories": ["0.5L"]}), p) is False


def test_zone_blocked_and_open():
    p = _Product()
    assert slotting.zone_accepts(_Zone({"blocked": True}), p) is False
    assert slotting.zone_accepts(_Zone({}), p) is True


def test_zone_abc_and_volume_bounds():
    p = _Product()
    assert slotting.zone_accepts(_Zone({"abc": ["A", "B"]}), p) is True
    assert slotting.zone_accepts(_Zone({"abc": ["C"]}), p) is False
    assert slotting.zone_accepts(_Zone({"max_volume_m3": 0.01}), p) is False
    assert slotting.zone_accepts(_Zone({"min_volume_m3": 0.01}), p) is True
