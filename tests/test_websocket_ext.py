"""Tests for WebSocket extended events (F-024)."""
import json
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from cove.api.routes.websocket import router

app = FastAPI()
app.include_router(router)


@pytest.mark.asyncio
async def test_agent_status_broadcast():
    """Send agent_status_update and verify broadcast and persistence."""
    mock_store = AsyncMock()
    mock_store.get_events.return_value = []

    with patch("cove.api.routes.websocket.SessionStoreService", return_value=mock_store):
        client = TestClient(app)
        with client.websocket_connect("/sessions/test-session/stream") as ws:
            # Receive the "connected" message
            connected = ws.receive_json()
            assert connected["type"] == "connected"
            assert connected["session_id"] == "test-session"

            # Send agent_status_update
            ws.send_json({
                "type": "agent_status_update",
                "agent_id": "worker-a",
                "status": "running",
                "progress": 0.4,
                "current_tool": "Edit",
            })

            # Verify broadcast received
            broadcast = ws.receive_json()
            assert broadcast["type"] == "agent_status"
            assert broadcast["agent_id"] == "worker-a"
            assert broadcast["status"] == "running"
            assert broadcast["progress"] == 0.4
            assert broadcast["current_tool"] == "Edit"

            # Verify persistence via store.emit_event
            mock_store.emit_event.assert_awaited_once_with(
                session_id="test-session",
                kind="agent_status",
                agent_id="worker-a",
                data={
                    "agent_id": "worker-a",
                    "status": "running",
                    "progress": 0.4,
                    "current_tool": "Edit",
                },
            )


@pytest.mark.asyncio
async def test_pipeline_update_broadcast():
    """Send pipeline_update and verify broadcast and persistence."""
    mock_store = AsyncMock()
    mock_store.get_events.return_value = []

    dag = {
        "nodes": [
            {"id": "planner", "status": "completed"},
            {"id": "worker-a", "status": "running"},
        ],
        "edges": [{"from": "planner", "to": "worker-a"}],
    }

    with patch("cove.api.routes.websocket.SessionStoreService", return_value=mock_store):
        client = TestClient(app)
        with client.websocket_connect("/sessions/test-session/stream") as ws:
            connected = ws.receive_json()
            assert connected["type"] == "connected"

            ws.send_json({"type": "pipeline_update", "dag": dag})

            broadcast = ws.receive_json()
            assert broadcast["type"] == "pipeline_update"
            assert broadcast["dag"] == dag

            mock_store.emit_event.assert_awaited_once_with(
                session_id="test-session",
                kind="pipeline_update",
                data={"dag": dag},
            )


@pytest.mark.asyncio
async def test_worker_progress_broadcast():
    """Send worker_progress and verify broadcast and persistence."""
    mock_store = AsyncMock()
    mock_store.get_events.return_value = []

    with patch("cove.api.routes.websocket.SessionStoreService", return_value=mock_store):
        client = TestClient(app)
        with client.websocket_connect("/sessions/test-session/stream") as ws:
            connected = ws.receive_json()
            assert connected["type"] == "connected"

            ws.send_json({
                "type": "worker_progress",
                "worker_id": "worker-a",
                "progress": 0.6,
                "message": "Writing jwt.py...",
            })

            broadcast = ws.receive_json()
            assert broadcast["type"] == "worker_progress"
            assert broadcast["worker_id"] == "worker-a"
            assert broadcast["progress"] == 0.6
            assert broadcast["message"] == "Writing jwt.py..."

            mock_store.emit_event.assert_awaited_once_with(
                session_id="test-session",
                kind="worker_progress",
                agent_id="worker-a",
                data={
                    "worker_id": "worker-a",
                    "progress": 0.6,
                    "message": "Writing jwt.py...",
                },
            )


@pytest.mark.asyncio
async def test_metrics_snapshot_broadcast():
    """Send metrics_snapshot and verify broadcast and persistence."""
    mock_store = AsyncMock()
    mock_store.get_events.return_value = []

    with patch("cove.api.routes.websocket.SessionStoreService", return_value=mock_store):
        client = TestClient(app)
        with client.websocket_connect("/sessions/test-session/stream") as ws:
            connected = ws.receive_json()
            assert connected["type"] == "connected"

            ws.send_json({
                "type": "metrics_snapshot",
                "active_agents": 3,
                "total_completed": 12,
                "cost_usd": 0.42,
                "uptime": 1080,
            })

            broadcast = ws.receive_json()
            assert broadcast["type"] == "metrics_snapshot"
            assert broadcast["active_agents"] == 3
            assert broadcast["total_completed"] == 12
            assert broadcast["cost_usd"] == 0.42
            assert broadcast["uptime"] == 1080

            mock_store.emit_event.assert_awaited_once_with(
                session_id="test-session",
                kind="metrics_snapshot",
                data={
                    "active_agents": 3,
                    "total_completed": 12,
                    "cost_usd": 0.42,
                    "uptime": 1080,
                },
            )


@pytest.mark.asyncio
async def test_multiple_clients_receive_broadcast():
    """Two clients on the same session both receive broadcast events."""
    mock_store = AsyncMock()
    mock_store.get_events.return_value = []

    with patch("cove.api.routes.websocket.SessionStoreService", return_value=mock_store):
        client = TestClient(app)
        with client.websocket_connect("/sessions/test-session/stream") as ws1:
            with client.websocket_connect("/sessions/test-session/stream") as ws2:
                # Both receive "connected" messages
                ws1.receive_json()
                ws2.receive_json()

                # Send message from ws1
                ws1.send_json({
                    "type": "agent_status_update",
                    "agent_id": "worker-b",
                    "status": "completed",
                    "progress": 1.0,
                    "current_tool": None,
                })

                # Both ws1 and ws2 should receive the broadcast
                broadcast1 = ws1.receive_json()
                broadcast2 = ws2.receive_json()

                for bcast in (broadcast1, broadcast2):
                    assert bcast["type"] == "agent_status"
                    assert bcast["agent_id"] == "worker-b"
                    assert bcast["status"] == "completed"
                    assert bcast["progress"] == 1.0
