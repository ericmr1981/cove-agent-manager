import os
from typing import Any

from cryptography.fernet import Fernet


class CredentialVault:
    """Simple encrypted credential store. In production, use HashiCorp Vault."""

    def __init__(self, key: str | None = None):
        self._key = key or os.environ.get("COVE_VAULT_KEY", Fernet.generate_key().decode())
        self._fernet = Fernet(self._key.encode() if isinstance(self._key, str) else self._key)
        self._store: dict[str, str] = {}

    def set(self, key: str, value: str) -> None:
        self._store[key] = self._fernet.encrypt(value.encode()).decode()

    def get(self, key: str) -> str | None:
        raw = self._store.get(key)
        if raw is None:
            return None
        return self._fernet.decrypt(raw.encode()).decode()

    def delete(self, key: str) -> None:
        self._store.pop(key, None)

    def list_keys(self) -> list[str]:
        return list(self._store.keys())
