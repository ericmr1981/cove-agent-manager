import pytest

from cove.harness.engine import HarnessEngine, SessionAlreadyCompleted
from cove.harness.mock_client import MockLLMClient
from cove.sandbox.manager import SandboxPool
from cove.sandbox.providers.local import LocalProvider
from cove.session_store.service import SessionStoreService


@pytest.fixture
def session_store():
    return SessionStoreService("sqlite+aiosqlite://")


@pytest.fixture
def sandbox_pool():
    return SandboxPool(provider=LocalProvider(), max_instances=5)


@pytest.fixture
def llm():
    return MockLLMClient()


@pytest.fixture
def engine(session_store, sandbox_pool, llm):
    return HarnessEngine(
        session_store=session_store,
        sandbox_pool=sandbox_pool,
        llm_client=llm,
    )


@pytest.mark.asyncio
async def test_wake_creates_instance(engine, session_store):
    session = await session_store.create_session("test-project")
    instance = await engine.wake(session["session_id"])
    assert instance.session_id == session["session_id"]
    assert not instance.completed


@pytest.mark.asyncio
async def test_wake_missing_session(engine):
    with pytest.raises(ValueError, match="not found"):
        await engine.wake("nonexistent")


@pytest.mark.asyncio
async def test_loop_yields_events(engine, session_store):
    session = await session_store.create_session("test-project")
    instance = await engine.wake(session["session_id"])
    events = []
    async for event in engine.loop(instance):
        events.append(event["type"])
    assert "event" in events
    assert "session_status" in events
    assert instance.completed


@pytest.mark.asyncio
async def test_wake_completed_session_raises(engine, session_store):
    session = await session_store.create_session("test-project")
    # Manually mark as completed via emit_event
    from cove.session_store.service import SessionStoreService
    # Can't easily update status through the current API
    # This test is a placeholder for when session update is added
    pass
