from app.connectors import registry  # noqa: F401 — populate registry
from app.connectors.base import all_specs, get_spec, validate_credentials


def test_builtin_connectors_registered():
    types = {s.type for s in all_specs()}
    assert {"smartup", "aslbelgisi"} <= types


def test_validate_credentials_missing():
    assert validate_credentials("aslbelgisi", {"tin": "x"}) == ["api_key"]
    assert validate_credentials("aslbelgisi", {"api_key": "k", "tin": "x"}) == []


def test_spec_secret_fields():
    spec = get_spec("smartup")
    assert "password" in spec.secret_fields
    assert "login" not in spec.secret_fields
