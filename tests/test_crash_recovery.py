from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from sqlalchemy import select

from cove.harness.crash_recovery import (
    CrashRecoveryManager,
    HEARTBEAT_CONFIG_KEY,
    HEARTBEAT_TIMEOUT_SECONDS,
)
from cove.session_store.models import SessionModel


@pytest_asyncio.fixture
async def manager(store):
    yield CrashRecoveryManager(store)


async def _set_session_running(
    store: SessionStoreService,
    session_id: str,
    heartbeat_delta: timedelta | None = None,
):
    """Set a session's status to 'running' and optionally configure its heartbeat."""
    async with store.session_factory() as db_session:
        model = await db_session.get(SessionModel, session_id)
        model.status = "running"
        if heartbeat_delta is not None:
            config = dict(model.config)
            ts = (datetime.now(timezone.utc) - heartbeat_delta).isoformat()
            config[HEARTBEAT_CONFIG_KEY] = ts
            model.config = config
        await db_session.commit()


async def _set_session_status(store: SessionStoreService, session_id: str, status: str):
    """Set a session's status directly."""
    async with store.session_factory() as db_session:
        model = await db_session.get(SessionModel, session_id)
        model.status = status
        await db_session.commit()


@pytest.mark.asyncio
async def test_detect_no_crash(manager, store):
    """Session with a recent heartbeat should not be detected as crashed."""
    created = await store.create_session("test-project")
    session_id = created["session_id"]

    # Mark running with a heartbeat from 5 seconds ago (under 30s timeout)
    await _set_session_running(store, session_id, heartbeat_delta=timedelta(seconds=5))

    assert await manager.detect_crashed(session_id) is False


@pytest.mark.asyncio
async def test_detect_crashed(manager, store):
    """Session with a stale heartbeat should be detected as crashed."""
    created = await store.create_session("test-project")
    session_id = created["session_id"]

    # Mark running with a heartbeat from well beyond the timeout
    stale_delta = timedelta(seconds=HEARTBEAT_TIMEOUT_SECONDS + 60)
    await _set_session_running(store, session_id, heartbeat_delta=stale_delta)

    assert await manager.detect_crashed(session_id) is True


@pytest.mark.asyncio
async def test_detect_no_heartbeat_ever(manager, store):
    """Session running but with no heartbeat record should be detected as crashed."""
    created = await store.create_session("test-project")
    session_id = created["session_id"]

    await _set_session_running(store, session_id, heartbeat_delta=None)

    assert await manager.detect_crashed(session_id) is True


@pytest.mark.asyncio
async def test_detect_not_running(manager, store):
    """Session in 'ready' status should not be detected as crashed."""
    created = await store.create_session("test-project")
    session_id = created["session_id"]

    assert await manager.detect_crashed(session_id) is False


@pytest.mark.asyncio
async def test_detect_nonexistent(manager):
    """Non-existent session should not be detected as crashed."""
    assert await manager.detect_crashed("nonexistent-id") is False


@pytest.mark.asyncio
async def test_recover_returns_state(manager, store):
    """Recovery returns correct state dict with last assistant_message / tool_result."""
    created = await store.create_session("test-project")
    session_id = created["session_id"]

    await _set_session_running(store, session_id)

    # Emit events in sequence
    await store.emit_event(session_id, "user_message", {"content": "hello"})
    await store.emit_event(session_id, "assistant_message", {"content": "Hi"})
    await store.emit_event(session_id, "tool_result", {"exit_code": 0, "stdout": "ok"})
    await store.emit_event(session_id, "user_message", {"content": "next"})

    result = await manager.recover(session_id)

    assert result["session_id"] == session_id
    # Last safe resume point is the tool_result at sequence 3
    assert result["last_event_sequence"] == 3
    assert result["last_event_kind"] == "tool_result"
    assert result["event_count"] == 4
    assert result["sandbox_needed"] is True
    assert result["status"] == "running"


@pytest.mark.asyncio
async def test_recover_no_events(manager, store):
    """Recovery on a session with no events returns None sequences."""
    created = await store.create_session("test-project")
    session_id = created["session_id"]

    await _set_session_running(store, session_id)

    result = await manager.recover(session_id)

    assert result["session_id"] == session_id
    assert result["last_event_sequence"] is None
    assert result["last_event_kind"] is None
    assert result["event_count"] == 0
    assert result["sandbox_needed"] is False
    assert result["status"] == "running"


@pytest.mark.asyncio
async def test_recover_only_user_messages(manager, store):
    """Session with only user_message events — no safe resume point found."""
    created = await store.create_session("test-project")
    session_id = created["session_id"]

    await _set_session_running(store, session_id)

    await store.emit_event(session_id, "user_message", {"content": "first"})
    await store.emit_event(session_id, "user_message", {"content": "second"})

    result = await manager.recover(session_id)

    assert result["session_id"] == session_id
    assert result["last_event_sequence"] is None
    assert result["last_event_kind"] is None
    assert result["event_count"] == 2
    assert result["sandbox_needed"] is True
    assert result["status"] == "running"


@pytest.mark.asyncio
async def test_recover_completed_session(manager, store):
    """Completed sessions are not recoverable — status 'completed' is returned."""
    created = await store.create_session("test-project")
    session_id = created["session_id"]

    await _set_session_status(store, session_id, "completed")

    result = await manager.recover(session_id)

    assert result["session_id"] == session_id
    assert result["last_event_sequence"] is None
    assert result["last_event_kind"] is None
    assert result["event_count"] == 0
    assert result["sandbox_needed"] is False
    assert result["status"] == "completed"


@pytest.mark.asyncio
async def test_recover_nonexistent(manager):
    """Non-existent session returns status 'not_found'."""
    result = await manager.recover("nonexistent-id")

    assert result["session_id"] == "nonexistent-id"
    assert result["status"] == "not_found"
    assert result["event_count"] == 0
    assert result["sandbox_needed"] is False


@pytest.mark.asyncio
async def test_heartbeat_updates_config(manager, store):
    """heartbeat() persists a timestamp in the session config."""
    created = await store.create_session("test-project")
    session_id = created["session_id"]

    await manager.heartbeat(session_id)

    session = await store.get_session(session_id)
    assert session is not None
    config = session.get("config", {})
    assert HEARTBEAT_CONFIG_KEY in config

    # Verify it's a valid ISO timestamp
    ts = datetime.fromisoformat(config[HEARTBEAT_CONFIG_KEY])
    assert ts.tzinfo is not None


@pytest.mark.asyncio
async def test_heartbeat_nonexistent(manager):
    """heartbeat() raises ValueError for non-existent session."""
    with pytest.raises(ValueError, match="nonexistent-id"):
        await manager.heartbeat("nonexistent-id")
