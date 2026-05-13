import asyncio
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from cove.harness.engine import HarnessEngine
from cove.session_store.service import SessionStoreService

logger = logging.getLogger(__name__)
router = APIRouter()


class ConnectionManager:
    """Manages WebSocket connections per session."""

    def __init__(self):
        self._connections: dict[str, set[WebSocket]] = {}

    async def connect(self, session_id: str, ws: WebSocket):
        await ws.accept()
        self._connections.setdefault(session_id, set()).add(ws)

    def disconnect(self, session_id: str, ws: WebSocket):
        self._connections.get(session_id, set()).discard(ws)
        if not self._connections.get(session_id):
            self._connections.pop(session_id, None)

    async def broadcast(self, session_id: str, event: dict):
        for ws in self._connections.get(session_id, set()).copy():
            try:
                await ws.send_json(event)
            except Exception:
                self._connections[session_id].discard(ws)

    def is_connected(self, session_id: str) -> bool:
        return bool(self._connections.get(session_id))


manager = ConnectionManager()


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

                elif msg_type == "interrupt":
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

            except json.JSONDecodeError:
                await ws.send_json({"type": "error", "code": "INVALID_JSON"})

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected: session=%s", session_id)
    finally:
        manager.disconnect(session_id, ws)
