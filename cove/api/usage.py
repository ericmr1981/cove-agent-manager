from datetime import datetime, timezone

from sqlalchemy import select, func

from cove.session_store.models import EventModel
from cove.session_store.service import SessionStoreService


class UsageTracker:
    """Tracks token usage and costs per session/project."""

    def __init__(self, store: SessionStoreService):
        self.store = store

    async def get_session_usage(self, session_id: str) -> dict:
        events = await self.store.get_events(session_id, limit=10000)
        total_tokens = sum(e.get("cost_tokens", 0) or 0 for e in events if "cost_tokens" in e)
        total_cost = sum(e.get("cost_usd", 0) or 0 for e in events if "cost_usd" in e)
        return {
            "session_id": session_id,
            "event_count": len(events),
            "total_tokens": total_tokens,
            "total_cost_usd": round(total_cost, 6),
        }
