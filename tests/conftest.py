"""Shared fixtures for Cove test suite — all tests use PostgreSQL by default."""

import os
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from cove.session_store.models import Base
from cove.session_store.service import SessionStoreService


@pytest.fixture(autouse=True)
def _clean_vault():
    """Clear vault persistence between tests to avoid cross-test leakage."""
    vault_path = Path(os.path.expanduser("~/.cove/vault.json"))
    if vault_path.exists():
        vault_path.unlink()
    yield

# Default to PostgreSQL; override via COVE_TEST_DATABASE_URL env var
TEST_DATABASE_URL = os.getenv(
    "COVE_TEST_DATABASE_URL",
    "postgresql+asyncpg://cove:cove-dev@localhost:5432/cove",
)


@pytest_asyncio.fixture
async def store():
    """SessionStoreService connected to PostgreSQL. Creates tables but does NOT drop
    on teardown (would destroy production data). Each test creates unique session IDs
    so cross-test isolation is maintained via distinct primary keys."""
    svc = SessionStoreService(TEST_DATABASE_URL)
    async with svc.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield svc
