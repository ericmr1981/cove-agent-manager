import json
import os
from pathlib import Path
from typing import Any

from cryptography.fernet import Fernet


_VAULT_DIR = Path(os.path.expanduser("~/.cove"))
_VAULT_PATH = _VAULT_DIR / "vault.json"
_KEY_PATH = _VAULT_DIR / "vault.key"


def _get_or_create_key() -> str:
    """Return stable Fernet key from key file, generating one if missing."""
    _VAULT_DIR.mkdir(parents=True, exist_ok=True)
    if _KEY_PATH.exists():
        return _KEY_PATH.read_text().strip()
    key = Fernet.generate_key().decode()
    _KEY_PATH.write_text(key)
    return key


class CredentialVault:
    """Encrypted credential store with file persistence.

    Stores encrypted values in ~/.cove/vault.json.
    Uses a stable key file at ~/.cove/vault.key so all processes share the same key.
    In production, replace with HashiCorp Vault.
    """

    def __init__(self, key: str | None = None):
        raw_key = key or os.environ.get("COVE_VAULT_KEY") or _get_or_create_key()
        self._fernet = Fernet(raw_key.encode() if isinstance(raw_key, str) else raw_key)
        self._store: dict[str, str] = self._load()

    def _load(self) -> dict[str, str]:
        if _VAULT_PATH.exists():
            return json.loads(_VAULT_PATH.read_text())
        return {}

    def _save(self):
        _VAULT_PATH.parent.mkdir(parents=True, exist_ok=True)
        _VAULT_PATH.write_text(json.dumps(self._store, indent=2))

    def set(self, key: str, value: str) -> None:
        self._store[key] = self._fernet.encrypt(value.encode()).decode()
        self._save()

    def get(self, key: str) -> str | None:
        raw = self._store.get(key)
        if raw is None:
            return None
        return self._fernet.decrypt(raw.encode()).decode()

    def delete(self, key: str) -> None:
        self._store.pop(key, None)
        self._save()

    def list_keys(self) -> list[str]:
        return list(self._store.keys())
