import pytest
import pytest_asyncio

from cove.session_store.service import SessionStoreService


@pytest_asyncio.fixture
async def service():
    svc = SessionStoreService("sqlite+aiosqlite://")
    await svc.create_tables()
    yield svc


@pytest.mark.asyncio
async def test_create_and_get_session(service):
    created = await service.create_session("test-project", {"model": "sonnet"})
    assert created["project_key"] == "test-project"

    fetched = await service.get_session(created["session_id"])
    assert fetched is not None
    assert fetched["project_key"] == "test-project"
    assert fetched["config"]["model"] == "sonnet"


@pytest.mark.asyncio
async def test_list_sessions(service):
    await service.create_session("proj-a")
    await service.create_session("proj-b")
    sessions = await service.list_sessions()
    assert len(sessions) >= 2


@pytest.mark.asyncio
async def test_emit_and_get_event(service):
    session = await service.create_session("test")
    event = await service.emit_event(session["session_id"], "user_message", {"content": "hello"})
    assert event["kind"] == "user_message"
    assert event["data"]["content"] == "hello"

    events = await service.get_events(session["session_id"])
    assert len(events) == 1
    assert events[0]["kind"] == "user_message"


@pytest.mark.asyncio
async def test_event_ordering(service):
    session = await service.create_session("test")
    e1 = await service.emit_event(session["session_id"], "user_message", {"n": 1})
    e2 = await service.emit_event(session["session_id"], "assistant_message", {"n": 2})
    events = await service.get_events(session["session_id"])
    assert [e["kind"] for e in events] == ["user_message", "assistant_message"]
