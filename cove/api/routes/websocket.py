import asyncio
import json
import logging
from pathlib import Path
import os

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from cove.harness.engine import HarnessEngine
from cove.sandbox.manager import SandboxPool
from cove.sandbox.providers.local import LocalProvider
from cove.harness.anthropic_client import AnthropicClient
from cove.harness.mock_client import MockLLMClient
from cove.harness.tool_router import ToolRouter
from cove.security.vault import CredentialVault
from cove.session_store.service import SessionStoreService

logger = logging.getLogger(__name__)
router = APIRouter()


class ConnectionManager:
    """Manages WebSocket connections per session."""

    def __init__(self):
        self._connections: dict[str, set[WebSocket]] = {}
        self._interrupted: set[str] = set()

    async def connect(self, session_id: str, ws: WebSocket):
        await ws.accept()
        self._connections.setdefault(session_id, set()).add(ws)
        self._interrupted.discard(session_id)

    def disconnect(self, session_id: str, ws: WebSocket):
        self._connections.get(session_id, set()).discard(ws)
        if not self._connections.get(session_id):
            self._connections.pop(session_id, None)
            self._interrupted.discard(session_id)

    async def broadcast(self, session_id: str, event: dict):
        for ws in self._connections.get(session_id, set()).copy():
            try:
                await ws.send_json(event)
            except Exception:
                self._connections[session_id].discard(ws)

    def is_connected(self, session_id: str) -> bool:
        return bool(self._connections.get(session_id))


manager = ConnectionManager()

# Sandbox pool shared across sessions
_sandbox_pool = SandboxPool(provider=LocalProvider(), max_instances=10)


def _load_model_config() -> dict:
    config_path = Path(os.path.expanduser("~/.cove/config.json"))
    if config_path.exists():
        return json.loads(config_path.read_text())
    return {}


def _build_llm_client():
    """Build LLM client from config — real AnthropicClient if key configured."""
    config = _load_model_config()
    vault = CredentialVault()
    api_key = vault.get("anthropic_api_key")
    if api_key:
        model = config.get("model", "claude-sonnet-4-20250514")
        return AnthropicClient(api_key=api_key, model=model)
    return MockLLMClient()


async def _run_harness(session_id: str):
    """Start HarnessEngine in background, broadcasting events via WebSocket."""
    try:
        store = SessionStoreService()
        llm = _build_llm_client()
        engine = HarnessEngine(
            session_store=store,
            sandbox_pool=_sandbox_pool,
            llm_client=llm,
            tool_router=ToolRouter(_sandbox_pool),
        )
        instance = await engine.wake(session_id)
        async for event in engine.loop(instance):
            await manager.broadcast(session_id, event)
            if session_id in manager._interrupted:
                break
    except Exception as e:
        logger.error("Harness engine error (session=%s): %s", session_id, e)
        await manager.broadcast(session_id, {"type": "error", "message": str(e)})


@router.websocket("/sessions/{session_id}/stream")
async def session_stream(ws: WebSocket, session_id: str):
    """WebSocket endpoint for real-time session events."""
    await manager.connect(session_id, ws)
    logger.info("WebSocket connected: session=%s", session_id)

    try:
        # Send existing events on connect
        store = SessionStoreService()
        events = await store.get_events(session_id, limit=50)
        await ws.send_json({"type": "connected", "session_id": session_id, "event_count": len(events)})

        # Listen for client messages
        while True:
            data = await ws.receive_text()
            try:
                msg = json.loads(data)
                msg_type = msg.get("type", "")

                if msg_type == "user_message":
                    await store.emit_event(
                        session_id=session_id,
                        kind="user_message",
                        data={"content": msg.get("content", ""), "id": msg.get("id", "")},
                    )
                    await ws.send_json({
                        "type": "event",
                        "event": {
                            "kind": "user_message",
                            "data": {"content": msg.get("content", "")},
                            "uuid": msg.get("id", ""),
                        },
                    })
                    # Start Harness engine in background
                    asyncio.create_task(_run_harness(session_id))

                elif msg_type == "interrupt":
                    manager._interrupted.add(session_id)
                    await ws.send_json({"type": "session_status", "status": "interrupted"})

                elif msg_type == "permission_response":
                    # Log permission decisions
                    await store.emit_event(
                        session_id=session_id,
                        kind="permission_decision",
                        data={
                            "request_id": msg.get("request_id", ""),
                            "decision": msg.get("decision", ""),
                        },
                    )

                elif msg_type == "agent_status_update":
                    agent_id = msg.get("agent_id", "")
                    status = msg.get("status", "")
                    progress = msg.get("progress")
                    current_tool = msg.get("current_tool")
                    await store.emit_event(
                        session_id=session_id,
                        kind="agent_status",
                        agent_id=agent_id,
                        data={
                            "agent_id": agent_id,
                            "status": status,
                            "progress": progress,
                            "current_tool": current_tool,
                        },
                    )
                    await manager.broadcast(
                        session_id,
                        {
                            "type": "agent_status",
                            "agent_id": agent_id,
                            "status": status,
                            "progress": progress,
                            "current_tool": current_tool,
                        },
                    )

                elif msg_type == "pipeline_update":
                    dag = msg.get("dag", {})
                    await store.emit_event(
                        session_id=session_id,
                        kind="pipeline_update",
                        data={"dag": dag},
                    )
                    await manager.broadcast(
                        session_id,
                        {"type": "pipeline_update", "dag": dag},
                    )

                elif msg_type == "worker_progress":
                    worker_id = msg.get("worker_id", "")
                    progress = msg.get("progress")
                    message = msg.get("message")
                    await store.emit_event(
                        session_id=session_id,
                        kind="worker_progress",
                        agent_id=worker_id,
                        data={
                            "worker_id": worker_id,
                            "progress": progress,
                            "message": message,
                        },
                    )
                    await manager.broadcast(
                        session_id,
                        {
                            "type": "worker_progress",
                            "worker_id": worker_id,
                            "progress": progress,
                            "message": message,
                        },
                    )

                elif msg_type == "metrics_snapshot":
                    payload = {
                        "active_agents": msg.get("active_agents"),
                        "total_completed": msg.get("total_completed"),
                        "cost_usd": msg.get("cost_usd"),
                        "uptime": msg.get("uptime"),
                    }
                    await store.emit_event(
                        session_id=session_id,
                        kind="metrics_snapshot",
                        data=payload,
                    )
                    await manager.broadcast(
                        session_id,
                        {"type": "metrics_snapshot", **payload},
                    )

            except json.JSONDecodeError:
                await ws.send_json({"type": "error", "code": "INVALID_JSON"})

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected: session=%s", session_id)
    finally:
        manager.disconnect(session_id, ws)
