from cove.session_store.service import SessionStoreService
from cove.sandbox.manager import SandboxPool, SandboxSpec


class SessionResumer:
    """Reconstructs a session from persisted events for resume."""

    def __init__(self, session_store: SessionStoreService, sandbox_pool: SandboxPool):
        self.store = session_store
        self.sandbox = sandbox_pool

    async def get_resume_state(self, session_id: str) -> dict:
        """Get the state needed to resume a session."""
        session = await self.store.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        events = await self.store.get_events(session_id, limit=1000)
        last_event = events[-1] if events else None

        sandbox_id = None
        config = session.get("config", {})
        if config.get("sandbox"):
            spec = SandboxSpec(image=config["sandbox"].get("image", "python:3.12-slim"))
            inst = await self.sandbox.provision(spec)
            sandbox_id = inst.id

        return {
            "session_id": session_id,
            "status": session.get("status", "unknown"),
            "event_count": len(events),
            "last_event_kind": last_event["kind"] if last_event else None,
            "sandbox_id": sandbox_id,
            "config": config,
        }

    async def get_event_slice(self, session_id: str, offset: int, limit: int = 100) -> list[dict]:
        return await self.store.get_events(session_id, offset, limit)
