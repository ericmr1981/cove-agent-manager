import pytest
import pytest_asyncio

from cove.harness.session_resume import SessionResumer
from cove.sandbox.manager import SandboxPool
from cove.sandbox.providers.local import LocalProvider


@pytest_asyncio.fixture
async def sandbox_pool():
    pool = SandboxPool(provider=LocalProvider(), max_instances=5)
    yield pool
    await pool.destroy_all()


@pytest_asyncio.fixture
async def resumer(store, sandbox_pool):
    return SessionResumer(session_store=store, sandbox_pool=sandbox_pool)


@pytest.mark.asyncio
async def test_get_resume_state(resumer, store):
    session = await store.create_session("test-project", {"model": "sonnet"})
    await store.emit_event(session["session_id"], "user_message", {"content": "hello"})
    await store.emit_event(session["session_id"], "assistant_message", {"content": "hi there"})

    state = await resumer.get_resume_state(session["session_id"])
    assert state["session_id"] == session["session_id"]
    assert state["status"] == "ready"
    assert state["event_count"] == 2
    assert state["last_event_kind"] == "assistant_message"
    assert state["config"]["model"] == "sonnet"
    assert state["sandbox_id"] is None  # no sandbox config


@pytest.mark.asyncio
async def test_resume_missing_session(resumer):
    with pytest.raises(ValueError, match="not found"):
        await resumer.get_resume_state("nonexistent-session-id")


@pytest.mark.asyncio
async def test_get_event_slice(resumer, store):
    session = await store.create_session("test-project")
    for i in range(10):
        await store.emit_event(session["session_id"], "test_event", {"index": i})

    # Get first 3 events
    slice_1 = await resumer.get_event_slice(session["session_id"], offset=0, limit=3)
    assert len(slice_1) == 3
    assert slice_1[0]["data"]["index"] == 0
    assert slice_1[2]["data"]["index"] == 2

    # Get next 3 events (offset 3)
    slice_2 = await resumer.get_event_slice(session["session_id"], offset=3, limit=3)
    assert len(slice_2) == 3
    assert slice_2[0]["data"]["index"] == 3
    assert slice_2[2]["data"]["index"] == 5

    # Get last 4 events
    slice_3 = await resumer.get_event_slice(session["session_id"], offset=7, limit=5)
    assert len(slice_3) == 3  # only 3 remaining from offset 7
    assert slice_3[0]["data"]["index"] == 7
    assert slice_3[-1]["data"]["index"] == 9


@pytest.mark.asyncio
async def test_resume_with_sandbox_config(resumer, store):
    session = await store.create_session("test-project", {"sandbox": {"image": "python:3.12-slim"}})
    await store.emit_event(session["session_id"], "user_message", {"content": "hello"})

    state = await resumer.get_resume_state(session["session_id"])
    assert state["sandbox_id"] is not None
    assert state["event_count"] == 1


@pytest.mark.asyncio
async def test_resume_no_events(resumer, store):
    session = await store.create_session("empty-project")
    state = await resumer.get_resume_state(session["session_id"])
    assert state["event_count"] == 0
    assert state["last_event_kind"] is None
