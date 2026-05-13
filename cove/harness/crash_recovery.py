from datetime import datetime, timezone
from typing import Any

from cove.session_store.service import SessionStoreService

HEARTBEAT_TIMEOUT_SECONDS = 30
HEARTBEAT_CONFIG_KEY = "_heartbeat"


class CrashRecoveryManager:
    """Detects crashed Harness instances and recovers session state.

    Implements the cattle pattern: Harness instances are stateless and
    disposable; all state lives in the Session Store. When a Harness
    goes silent (no heartbeat within the timeout window), a new instance
    can resume from the last persisted event.
    """

    def __init__(self, store: SessionStoreService):
        self.store = store

    async def detect_crashed(self, session_id: str) -> bool:
        """Check if a running session has gone silent (heartbeat timeout)."""
        session = await self.store.get_session(session_id)
        if session is None:
            return False
        if session["status"] != "running":
            return False

        config = session.get("config", {})
        heartbeat_str = config.get(HEARTBEAT_CONFIG_KEY)
        if heartbeat_str is None:
            # Session is marked running but has no heartbeat record — treat as crashed.
            return True

        try:
            heartbeat = datetime.fromisoformat(heartbeat_str)
        except (ValueError, TypeError):
            return True

        elapsed = (datetime.now(timezone.utc) - heartbeat).total_seconds()
        return elapsed > HEARTBEAT_TIMEOUT_SECONDS

    async def recover(self, session_id: str) -> dict[str, Any]:
        """Load session state and return resume context.

        Returns a dict with:
          - session_id
          - last_event_sequence (int | None)
          - last_event_kind (str | None)
          - event_count (int)
          - sandbox_needed (bool)
          - status (str)
        """
        session = await self.store.get_session(session_id)
        if session is None:
            return {
                "session_id": session_id,
                "last_event_sequence": None,
                "last_event_kind": None,
                "event_count": 0,
                "sandbox_needed": False,
                "status": "not_found",
            }

        if session["status"] == "completed":
            return {
                "session_id": session_id,
                "last_event_sequence": None,
                "last_event_kind": None,
                "event_count": 0,
                "sandbox_needed": False,
                "status": "completed",
            }

        events = await self.store.get_events(session_id)
        event_count = len(events)

        # Walk backwards to find the last safe resume point
        last_event_sequence: int | None = None
        last_event_kind: str | None = None
        for event in reversed(events):
            if event["kind"] in ("assistant_message", "tool_result"):
                last_event_sequence = event["sequence"]
                last_event_kind = event["kind"]
                break

        sandbox_needed = event_count > 0

        return {
            "session_id": session_id,
            "last_event_sequence": last_event_sequence,
            "last_event_kind": last_event_kind,
            "event_count": event_count,
            "sandbox_needed": sandbox_needed,
            "status": session["status"],
        }

    async def heartbeat(self, session_id: str) -> None:
        """Record a heartbeat timestamp for the session."""
        session = await self.store.get_session(session_id)
        if session is None:
            raise ValueError(f"Session {session_id} not found")

        config_updates = {
            HEARTBEAT_CONFIG_KEY: datetime.now(timezone.utc).isoformat(),
        }
        result = await self.store.update_session_config(session_id, config_updates)
        if result is None:
            raise ValueError(f"Failed to update session {session_id}")
