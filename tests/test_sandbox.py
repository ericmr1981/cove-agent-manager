import pytest

from cove.sandbox.manager import SandboxPool, SandboxSpec
from cove.sandbox.providers.local import LocalProvider


@pytest.fixture
def pool():
    return SandboxPool(provider=LocalProvider(), max_instances=5)


@pytest.mark.asyncio
async def test_create_and_execute(pool):
    instance = await pool.provision(SandboxSpec(image="local"))
    assert instance.status == "running"

    result = await pool.execute(instance.id, "echo hello")
    assert "hello" in result


@pytest.mark.asyncio
async def test_multiple_commands(pool):
    instance = await pool.provision()
    r1 = await pool.execute(instance.id, "echo foo")
    r2 = await pool.execute(instance.id, "echo bar")
    assert "foo" in r1
    assert "bar" in r2


@pytest.mark.asyncio
async def test_destroy_removes_instance(pool):
    instance = await pool.provision()
    await pool.destroy(instance.id)
    with pytest.raises(ValueError):
        await pool.execute(instance.id, "echo")


@pytest.mark.asyncio
async def test_pool_max_instances(pool):
    for _ in range(5):
        await pool.provision()
    with pytest.raises(RuntimeError, match="pool exhausted"):
        await pool.provision()
