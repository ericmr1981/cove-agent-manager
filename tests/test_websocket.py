import pytest


@pytest.mark.asyncio
async def test_websocket_router_exists():
    from cove.api.routes.websocket import router, ConnectionManager
    assert router is not None
    mgr = ConnectionManager()
    assert mgr._connections == {}
