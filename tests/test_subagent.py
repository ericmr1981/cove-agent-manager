import pytest
import pytest_asyncio

from cove.orchestration.subagent import SubAgentOrchestrator, SubAgentTask
from cove.sandbox.manager import SandboxPool
from cove.sandbox.providers.local import LocalProvider


@pytest_asyncio.fixture
async def sandbox_pool():
    pool = SandboxPool(provider=LocalProvider(), max_instances=10)
    yield pool
    await pool.destroy_all()


@pytest_asyncio.fixture
async def orchestrator(store, sandbox_pool):
    return SubAgentOrchestrator(session_store=store, sandbox_pool=sandbox_pool)


@pytest.mark.asyncio
async def test_run_parallel(orchestrator):
    tasks = [
        SubAgentTask(name="task-a"),
        SubAgentTask(name="task-b"),
    ]
    results = await orchestrator.run_parallel(tasks)

    assert len(results) == 2
    for task in results:
        assert task.status == "completed"
        assert task.id != ""


@pytest.mark.asyncio
async def test_run_sequential(orchestrator):
    tasks = [
        SubAgentTask(name="task-1"),
        SubAgentTask(name="task-2"),
        SubAgentTask(name="task-3"),
    ]
    results = await orchestrator.run_sequential(tasks)

    assert len(results) == 3
    for task in results:
        assert task.status == "completed"
        assert task.id != ""


@pytest.mark.asyncio
async def test_task_lifecycle(orchestrator):
    tasks = [
        SubAgentTask(name="lifecycle-test"),
    ]
    # Verify initial state
    assert tasks[0].status == "pending"
    assert tasks[0].id == ""

    results = await orchestrator.run_parallel(tasks)

    # Verify completed state
    assert results[0].status == "completed"
    assert results[0].id != ""
    assert results[0].name == "lifecycle-test"


@pytest.mark.asyncio
async def test_empty_tasks(orchestrator):
    results = await orchestrator.run_parallel([])
    assert results == []

    results = await orchestrator.run_sequential([])
    assert results == []


@pytest.mark.asyncio
async def test_single_task(orchestrator):
    tasks = [SubAgentTask(name="single")]
    results = await orchestrator.run_parallel(tasks)
    assert len(results) == 1
    assert results[0].status == "completed"
