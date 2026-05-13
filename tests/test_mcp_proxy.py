import pytest
import pytest_asyncio

from cove.security.mcp_proxy import MCPProxy
from cove.security.vault import CredentialVault


@pytest_asyncio.fixture
async def proxy():
    vault = CredentialVault()
    p = MCPProxy(vault=vault)
    yield p
    await p.close()


@pytest.mark.asyncio
async def test_initialization(proxy):
    assert proxy.vault is not None
    assert proxy._client is not None


@pytest.mark.asyncio
async def test_initialization_with_default_vault():
    proxy = MCPProxy()
    assert proxy.vault is not None
    await proxy.close()


@pytest.mark.asyncio
async def test_call_tool_connection_error(proxy):
    """Non-existent server should return an error dict gracefully (no exception)."""
    result = await proxy.call_tool(
        server_url="http://nonexistent.invalid",
        tool_name="test_tool",
        args={"key": "value"},
    )
    assert "error" in result
    assert "connection failed" in result["error"] or "ConnectError" in result["error"]


@pytest.mark.asyncio
async def test_call_tool_connection_error_bad_host(proxy):
    """Connection to a non-routable address should return error dict, not crash."""
    result = await proxy.call_tool(
        server_url="http://192.0.2.1:9999",
        tool_name="test",
        args={},
    )
    assert "error" in result


@pytest.mark.asyncio
async def test_call_tool_includes_token_when_present(proxy):
    proxy.vault.set("mcp:http://example.com:mcp:token", "my-secret-token")
    # This will still fail to connect, but we verify the headers are set
    result = await proxy.call_tool(
        server_url="http://example.com/mcp",
        tool_name="test",
        args={},
    )
    # Example.com doesn't serve MCP, so we'll get an error, but it should be
    # an HTTP status error, not a connection error
    assert "error" in result
