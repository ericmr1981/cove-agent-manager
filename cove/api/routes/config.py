import json
import os
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from cove.security.vault import CredentialVault

router = APIRouter()
vault = CredentialVault()

CONFIG_PATH = Path(os.path.expanduser("~/.cove/config.json"))


class ConfigUpdate(BaseModel):
    model: str | None = None
    temperature: float | None = None
    max_tokens: int | None = None
    api_endpoint: str | None = None


class VaultUpdate(BaseModel):
    value: str


def _load_config() -> dict:
    if CONFIG_PATH.exists():
        return json.loads(CONFIG_PATH.read_text())
    return {}


def _save_config(config: dict):
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(config, indent=2))


@router.get("/config")
async def get_config():
    return _load_config()


@router.put("/config")
async def update_config(body: ConfigUpdate):
    config = _load_config()
    if body.model is not None:
        config["model"] = body.model
    if body.temperature is not None:
        config["temperature"] = body.temperature
    if body.max_tokens is not None:
        config["max_tokens"] = body.max_tokens
    if body.api_endpoint is not None:
        config["api_endpoint"] = body.api_endpoint
    _save_config(config)
    return {"status": "ok", "config": config}


@router.put("/vault/{key_name}")
async def set_vault_key(key_name: str, body: VaultUpdate):
    if key_name in ("anthropic_api_key", "openai_api_key"):
        vault.set(key_name, body.value)
        return {"status": "ok"}
    raise HTTPException(status_code=400, detail=f"Unknown key: {key_name}")


@router.delete("/vault/{key_name}")
async def delete_vault_key(key_name: str):
    vault.delete(key_name)
    return {"status": "ok"}
