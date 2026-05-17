"""Phase 3: envelope encryption tests."""

import pytest

from app.core import crypto


def test_encrypt_decrypt_roundtrip():
    enc = crypto.encrypt_secret("super-secret-api-key")
    assert enc.ciphertext != "super-secret-api-key"
    assert enc.encrypted_dek != enc.ciphertext
    assert crypto.decrypt_secret(enc.encrypted_dek, enc.ciphertext) == "super-secret-api-key"


def test_each_encryption_uses_fresh_data_key():
    a = crypto.encrypt_secret("same-value")
    b = crypto.encrypt_secret("same-value")
    assert a.encrypted_dek != b.encrypted_dek
    assert a.ciphertext != b.ciphertext


def test_wrong_master_key_cannot_decrypt(monkeypatch):
    enc = crypto.encrypt_secret("value")

    class _Other:
        master_key = "a-totally-different-master-key"

    monkeypatch.setattr(crypto, "get_settings", lambda: _Other())
    with pytest.raises(crypto.DecryptionError):
        crypto.decrypt_secret(enc.encrypted_dek, enc.ciphertext)
