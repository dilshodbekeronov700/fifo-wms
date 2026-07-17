from app.core import crypto


def test_encrypt_roundtrip():
    creds = {"api_key": "SECRET", "tin": "307797292", "business_place_id": 27}
    enc = crypto.encrypt_credentials(creds)
    assert set(enc.keys()) == {"_enc"}
    assert "SECRET" not in enc["_enc"]
    assert crypto.decrypt_credentials(enc) == creds


def test_legacy_plaintext_passthrough():
    plain = {"login": "a", "password": "b"}
    assert not crypto.is_credentials_encrypted(plain)
    assert crypto.decrypt_credentials(plain) == plain
