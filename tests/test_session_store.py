import pytest

from cove.session_store.service import SessionStoreService


@pytest.mark.asyncio
async def test_create_and_get_session(store):
    created = await store.create_session("test-project", {"model": "sonnet"})
    assert created["project_key"] == "test-project"

    fetched = await store.get_session(created["session_id"])
    assert fetched is not None
    assert fetched["project_key"] == "test-project"
    assert fetched["config"]["model"] == "sonnet"


@pytest.mark.asyncio
async def test_list_sessions(store):
    await store.create_session("proj-a")
    await store.create_session("proj-b")
    sessions = await store.list_sessions()
    assert len(sessions) >= 2


@pytest.mark.asyncio
async def test_emit_and_get_event(store):
    session = await store.create_session("test")
    event = await store.emit_event(session["session_id"], "user_message", {"content": "hello"})
    assert event["kind"] == "user_message"
    assert event["data"]["content"] == "hello"

    events = await store.get_events(session["session_id"])
    assert len(events) == 1
    assert events[0]["kind"] == "user_message"


@pytest.mark.asyncio
async def test_event_ordering(store):
    session = await store.create_session("test")
    await store.emit_event(session["session_id"], "user_message", {"n": 1})
    await store.emit_event(session["session_id"], "assistant_message", {"n": 2})
    events = await store.get_events(session["session_id"])
    assert [e["kind"] for e in events] == ["user_message", "assistant_message"]
