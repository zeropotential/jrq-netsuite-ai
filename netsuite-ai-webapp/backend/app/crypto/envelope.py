import base64
import os
from dataclasses import dataclass

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class CryptoError(RuntimeError):
    pass


@dataclass(frozen=True)
class EncryptedSecret:
    key_id: str
    aad: bytes
    wrapped_dek: bytes
    wrapped_dek_nonce: bytes
    data_nonce: bytes
    ciphertext: bytes


def _b64decode_required(value_b64: str, *, name: str) -> bytes:
    if not value_b64:
        raise CryptoError(f"Missing required {name}")
    try:
        return base64.b64decode(value_b64)
    except Exception as exc:  # pragma: no cover
        raise CryptoError(f"Invalid base64 for {name}") from exc


def encrypt_secret(*, plaintext: bytes, kek_b64: str, key_id: str, aad: bytes) -> EncryptedSecret:
    """Envelope-encrypts a secret for storage.

    - Generates a random DEK (32 bytes)
    - Encrypts plaintext with DEK using AES-256-GCM
    - Wraps DEK with KEK using AES-256-GCM

    Store all returned fields in Postgres (BYTEA).
    """

    kek = _b64decode_required(kek_b64, name="APP_KEK_B64")
    if len(kek) != 32:
        raise CryptoError("APP_KEK_B64 must decode to 32 bytes (AES-256 key)")
    if not key_id:
        raise CryptoError("key_id is required")

    dek = os.urandom(32)

    data_nonce = os.urandom(12)
    ciphertext = AESGCM(dek).encrypt(data_nonce, plaintext, aad)

    wrapped_dek_nonce = os.urandom(12)
    wrapped_dek = AESGCM(kek).encrypt(wrapped_dek_nonce, dek, aad)

    return EncryptedSecret(
        key_id=key_id,
        aad=aad,
        wrapped_dek=wrapped_dek,
        wrapped_dek_nonce=wrapped_dek_nonce,
        data_nonce=data_nonce,
        ciphertext=ciphertext,
    )


def decrypt_secret(*, enc: EncryptedSecret, kek_b64: str) -> bytes:
    kek = _b64decode_required(kek_b64, name="APP_KEK_B64")
    if len(kek) != 32:
        raise CryptoError("APP_KEK_B64 must decode to 32 bytes (AES-256 key)")

    try:
        dek = AESGCM(kek).decrypt(enc.wrapped_dek_nonce, enc.wrapped_dek, enc.aad)
        return AESGCM(dek).decrypt(enc.data_nonce, enc.ciphertext, enc.aad)
    except Exception as exc:
        raise CryptoError("Secret decryption failed") from exc
