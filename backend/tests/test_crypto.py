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


def test_rewrap_dek_rotates_master_key(monkeypatch):
    # Encrypt under the default (dev) master key.
    enc = crypto.encrypt_secret("rotate-me")
    old_key = crypto.get_settings().master_key
    new_key = "brand-new-master-key-value"

    new_dek = crypto.rewrap_dek(old_key, new_key, enc.encrypted_dek)
    assert new_dek != enc.encrypted_dek

    # The ciphertext is unchanged; decryption now works under the new key.
    class _New:
        master_key = new_key

    monkeypatch.setattr(crypto, "get_settings", lambda: _New())
    assert crypto.decrypt_secret(new_dek, enc.ciphertext) == "rotate-me"
    # Old wrapped DEK no longer decrypts under the new key.
    with pytest.raises(crypto.DecryptionError):
        crypto.decrypt_secret(enc.encrypted_dek, enc.ciphertext)


def test_rewrap_dek_rejects_wrong_old_key():
    enc = crypto.encrypt_secret("x")
    with pytest.raises(crypto.DecryptionError):
        crypto.rewrap_dek("not-the-old-key", "new-key", enc.encrypted_dek)
