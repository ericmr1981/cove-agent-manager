import pytest
import pytest_asyncio

from cove.harness.tool_router import ToolRouter
from cove.sandbox.manager import SandboxPool
from cove.sandbox.providers.local import LocalProvider


@pytest_asyncio.fixture
async def router():
    pool = SandboxPool(provider=LocalProvider(), max_instances=5)
    inst = await pool.provision()
    router = ToolRouter(sandbox_pool=pool)
    yield router, inst.id
    await pool.destroy_all()


@pytest.mark.asyncio
async def test_execute_bash(router):
    tr, sandbox_id = router
    result = await tr.execute("Bash", {"command": "echo hello world"}, sandbox_id)
    assert "content" in result
    assert "hello world" in result["content"]


@pytest.mark.asyncio
async def test_execute_read(router):
    tr, sandbox_id = router
    # Write a temp file first via bash, then read it
    await tr.execute("Bash", {"command": "echo 'file content' > /tmp/test_read.txt"}, sandbox_id)
    result = await tr.execute("Read", {"file_path": "/tmp/test_read.txt"}, sandbox_id)
    assert "content" in result
    assert "file content" in result["content"]


@pytest.mark.asyncio
async def test_execute_edit(router):
    tr, sandbox_id = router
    await tr.execute("Bash", {"command": "echo 'hello world' > /tmp/test_edit.txt"}, sandbox_id)
    result = await tr.execute("Edit", {
        "file_path": "/tmp/test_edit.txt",
        "old_string": "hello",
        "new_string": "hi",
    }, sandbox_id)
    assert "content" in result
    assert "Edited /tmp/test_edit.txt" in result["content"]


@pytest.mark.asyncio
async def test_unknown_tool(router):
    tr, _ = router
    result = await tr.execute("NonExistentTool", {}, "some-id")
    assert "error" in result
    assert "Unknown tool" in result["error"]


@pytest.mark.asyncio
async def test_execute_no_sandbox(router):
    tr, _ = router
    result = await tr.execute("Bash", {"command": "echo hello"}, None)
    assert "content" in result
    assert "[cove]" in result["content"]
