"""Envelope encryption for secrets at rest.

Each secret is encrypted with a freshly generated data key (DEK). The DEK is
then encrypted with a key-encryption key (KEK) derived from the application
master key. Only the encrypted DEK and ciphertext are stored; the plaintext
DEK never touches disk.
"""

import base64

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from app.core.config import get_settings


class DecryptionError(Exception):
    """Raised when ciphertext cannot be decrypted with the current master key."""


def _kek() -> Fernet:
    master = get_settings().master_key.encode()
    derived = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b"trading-bot-envelope-v1",
        info=b"key-encryption-key",
    ).derive(master)
    return Fernet(base64.urlsafe_b64encode(derived))


class EncryptedSecret:
    """Bundle of an encrypted data key and the ciphertext it protects."""

    __slots__ = ("encrypted_dek", "ciphertext")

    def __init__(self, encrypted_dek: str, ciphertext: str) -> None:
        self.encrypted_dek = encrypted_dek
        self.ciphertext = ciphertext


def encrypt_secret(plaintext: str) -> EncryptedSecret:
    dek = Fernet.generate_key()
    ciphertext = Fernet(dek).encrypt(plaintext.encode()).decode()
    encrypted_dek = _kek().encrypt(dek).decode()
    return EncryptedSecret(encrypted_dek=encrypted_dek, ciphertext=ciphertext)


def decrypt_secret(encrypted_dek: str, ciphertext: str) -> str:
    try:
        dek = _kek().decrypt(encrypted_dek.encode())
        return Fernet(dek).decrypt(ciphertext.encode()).decode()
    except InvalidToken as exc:
        raise DecryptionError("Unable to decrypt secret with the current master key") from exc
