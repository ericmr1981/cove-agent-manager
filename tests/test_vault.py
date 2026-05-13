import base64

import pytest
from cove.security.vault import CredentialVault

# Fernet requires a 32-byte URL-safe base64-encoded key
_TEST_KEY = base64.urlsafe_b64encode(b"x" * 32).decode()


def test_vault_set_and_get():
    v = CredentialVault(key=_TEST_KEY)
    v.set("api-key", "sk-12345")
    assert v.get("api-key") == "sk-12345"


def test_vault_missing_key():
    v = CredentialVault(key=_TEST_KEY)
    assert v.get("nonexistent") is None


def test_vault_list_keys():
    v = CredentialVault(key=_TEST_KEY)
    v.set("a", "1")
    v.set("b", "2")
    assert set(v.list_keys()) == {"a", "b"}
