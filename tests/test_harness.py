import pytest

from cove.harness.engine import HarnessEngine
from cove.harness.mock_client import MockLLMClient
from cove.harness.permissions import PermissionSystem
from cove.sandbox.manager import SandboxPool
from cove.sandbox.providers.local import LocalProvider
from cove.harness.tool_router import ToolRouter


@pytest.fixture
def sandbox_pool():
    return SandboxPool(provider=LocalProvider(), max_instances=5)


@pytest.fixture
def llm():
    return MockLLMClient()


@pytest.fixture
def engine(store, sandbox_pool, llm):
    return HarnessEngine(
        session_store=store,
        sandbox_pool=sandbox_pool,
        llm_client=llm,
    )


@pytest.mark.asyncio
async def test_wake_creates_instance(engine, store):
    session = await store.create_session("test-project")
    instance = await engine.wake(session["session_id"])
    assert instance.session_id == session["session_id"]
    assert not instance.completed


@pytest.mark.asyncio
async def test_wake_missing_session(engine):
    with pytest.raises(ValueError, match="not found"):
        await engine.wake("nonexistent")


@pytest.mark.asyncio
async def test_loop_yields_events(engine, store):
    session = await store.create_session("test-project")
    instance = await engine.wake(session["session_id"])
    events = []
    async for event in engine.loop(instance):
        events.append(event["type"])
    assert "event" in events
    assert "session_status" in events
    assert instance.completed


@pytest.mark.asyncio
async def test_loop_processes_tool_use(store, sandbox_pool):
    """LLM response with tool_use triggers execution and result injection."""
    tool_use_responses = [[
        {"type": "content_block_delta", "text": "Let me check the project structure."},
        {"type": "tool_use_start", "id": "toolu_01", "name": "Bash", "index": 1},
        {"type": "tool_use_end", "id": "toolu_01", "name": "Bash", "input": {"command": "ls -la"}},
    ]]
    llm = MockLLMClient(responses=tool_use_responses)
    tool_router = ToolRouter(sandbox_pool)
    engine = HarnessEngine(
        session_store=store,
        sandbox_pool=sandbox_pool,
        llm_client=llm,
        tool_router=tool_router,
    )
    session = await store.create_session("tool-test")
    instance = await engine.wake(session["session_id"])
    raw_events: list[dict] = []
    async for event in engine.loop(instance):
        raw_events.append(event)
    kinds = {e["event"]["kind"] for e in raw_events if e.get("type") == "event"}
    assert "tool_use" in kinds
    assert "tool_result" in kinds
    assert instance.completed


@pytest.mark.asyncio
async def test_tool_use_permission_check(store, sandbox_pool):
    """Dangerous tool_use triggers permission_request yield."""
    tool_use_responses = [[
        {"type": "tool_use_start", "id": "toolu_02", "name": "Bash", "index": 0},
        {"type": "tool_use_end", "id": "toolu_02", "name": "Bash", "input": {"command": "rm -rf /"}},
    ]]
    llm = MockLLMClient(responses=tool_use_responses)
    permissions = PermissionSystem(mode="acceptEdits")
    engine = HarnessEngine(
        session_store=store,
        sandbox_pool=sandbox_pool,
        llm_client=llm,
        permission_system=permissions,
    )
    session = await store.create_session("perm-test")
    instance = await engine.wake(session["session_id"])
    event_types: list[str] = []
    async for event in engine.loop(instance):
        event_types.append(event["type"] if isinstance(event, dict) else str(event))
    assert "permission_request" in event_types
    assert instance.completed


@pytest.mark.asyncio
async def test_tool_use_bypass_permissions(store, sandbox_pool):
    """bypassPermissions mode allows tool_use without approval."""
    tool_use_responses = [[
        {"type": "tool_use_start", "id": "toolu_03", "name": "Bash", "index": 0},
        {"type": "tool_use_end", "id": "toolu_03", "name": "Bash", "input": {"command": "echo hello"}},
    ]]
    llm = MockLLMClient(responses=tool_use_responses)
    permissions = PermissionSystem(mode="bypassPermissions")
    engine = HarnessEngine(
        session_store=store,
        sandbox_pool=sandbox_pool,
        llm_client=llm,
        permission_system=permissions,
    )
    session = await store.create_session("bypass-test")
    instance = await engine.wake(session["session_id"])
    raw_events: list[dict] = []
    async for event in engine.loop(instance):
        raw_events.append(event)
    kinds = {e["event"]["kind"] for e in raw_events if e.get("type") == "event"}
    assert "tool_result" in kinds
    assert instance.completed
