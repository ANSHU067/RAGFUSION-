"""Authenticated encryption and in-memory API-key lifecycle management."""

from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import datetime, timezone

from cryptography.fernet import Fernet, InvalidToken


class EncryptionError(ValueError):
    """Raised when encrypted data cannot be authenticated or decrypted."""


class APIKeyCipher:
    """Encrypt API keys at rest using Fernet (AES-128-CBC plus HMAC)."""

    def __init__(self, key: str | bytes) -> None:
        try:
            self._fernet = Fernet(key.encode() if isinstance(key, str) else key)
        except (ValueError, TypeError) as exc:
            raise EncryptionError("encryption key must be a Fernet key") from exc

    @staticmethod
    def generate_encryption_key() -> str:
        return Fernet.generate_key().decode()

    def encrypt(self, plaintext: str) -> str:
        if not plaintext:
            raise EncryptionError("cannot encrypt an empty secret")
        return self._fernet.encrypt(plaintext.encode()).decode()

    def decrypt(self, ciphertext: str) -> str:
        try:
            return self._fernet.decrypt(ciphertext.encode()).decode()
        except (InvalidToken, UnicodeDecodeError) as exc:
            raise EncryptionError("invalid encrypted secret") from exc


@dataclass(slots=True)
class StoredAPIKey:
    key_id: str
    encrypted_value: str
    digest: str
    created_at: datetime
    revoked_at: datetime | None = None


class APIKeyManager:
    """Secure API-key manager with a replaceable storage boundary.

    The default in-memory store is appropriate for a single process and tests;
    production deployments should persist ``StoredAPIKey`` records in a secret-backed database.
    """

    def __init__(self, cipher: APIKeyCipher) -> None:
        self._cipher = cipher
        self._keys: dict[str, StoredAPIKey] = {}

    def generate(self) -> tuple[str, str]:
        key_id = secrets.token_urlsafe(12)
        secret = f"dpk_{secrets.token_urlsafe(32)}"
        self._keys[key_id] = StoredAPIKey(
            key_id,
            self._cipher.encrypt(secret),
            self._digest(secret),
            datetime.now(timezone.utc),
        )
        return key_id, secret

    def validate(self, presented_key: str) -> str | None:
        digest = self._digest(presented_key)
        for record in self._keys.values():
            if record.revoked_at is None and hmac.compare_digest(record.digest, digest):
                return record.key_id
        return None

    def rotate(self, key_id: str) -> tuple[str, str]:
        self.revoke(key_id)
        return self.generate()

    def revoke(self, key_id: str) -> None:
        record = self._keys.get(key_id)
        if record is None:
            raise KeyError("API key not found")
        record.revoked_at = datetime.now(timezone.utc)

    def encrypted_value(self, key_id: str) -> str:
        return self._keys[key_id].encrypted_value

    @staticmethod
    def _digest(value: str) -> str:
        return hashlib.sha256(value.encode()).hexdigest()
