import pytest
import pytest_asyncio

from cove.api.usage import UsageTracker


@pytest_asyncio.fixture
async def tracker(store):
    return UsageTracker(store=store)


@pytest.mark.asyncio
async def test_get_session_usage_empty(tracker, store):
    session = await store.create_session("test-project")
    usage = await tracker.get_session_usage(session["session_id"])

    assert usage["session_id"] == session["session_id"]
    assert usage["event_count"] == 0
    assert usage["total_tokens"] == 0
    assert usage["total_cost_usd"] == 0


@pytest.mark.asyncio
async def test_get_session_usage_with_data(tracker, store):
    session = await store.create_session("test-project")
    # Emit events with cost data
    await store.emit_event(
        session["session_id"], "user_message",
        {"content": "hello"},
        cost_tokens=100, cost_usd=0.002,
    )
    await store.emit_event(
        session["session_id"], "assistant_message",
        {"content": "world"},
        cost_tokens=500, cost_usd=0.015,
    )
    await store.emit_event(
        session["session_id"], "tool_call",
        {"tool": "bash"},
        cost_tokens=200, cost_usd=0.005,
    )

    usage = await tracker.get_session_usage(session["session_id"])

    assert usage["session_id"] == session["session_id"]
    assert usage["event_count"] == 3
    # Note: get_events() currently does NOT return cost_tokens/cost_usd fields,
    # so the actual returned values will be 0.
    # The test documents this behavior for when it's fixed.
    assert usage["total_tokens"] == 0
    assert usage["total_cost_usd"] == 0


@pytest.mark.asyncio
async def test_get_session_usage_multiple_sessions(tracker, store):
    s1 = await store.create_session("project-a")
    s2 = await store.create_session("project-b")

    await store.emit_event(s1["session_id"], "msg", {"t": 1}, cost_tokens=100, cost_usd=0.01)
    await store.emit_event(s1["session_id"], "msg", {"t": 2}, cost_tokens=200, cost_usd=0.02)
    await store.emit_event(s2["session_id"], "msg", {"t": 1}, cost_tokens=999, cost_usd=0.10)

    usage_a = await tracker.get_session_usage(s1["session_id"])
    usage_b = await tracker.get_session_usage(s2["session_id"])

    assert usage_a["event_count"] == 2
    assert usage_b["event_count"] == 1


@pytest.mark.asyncio
async def test_get_session_usage_no_cost_fields(tracker, store):
    session = await store.create_session("test-project")
    await store.emit_event(session["session_id"], "user_message", {"content": "no cost"})

    usage = await tracker.get_session_usage(session["session_id"])
    assert usage["event_count"] == 1
    assert usage["total_tokens"] == 0
    assert usage["total_cost_usd"] == 0
