import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import datetime, timezone

from cove.harness.context_builder import ContextBuilder
from cove.harness.llm_client import LLMProvider
from cove.harness.permissions import PermissionSystem
from cove.harness.tool_router import ToolRouter
from cove.sandbox.manager import SandboxPool, SandboxSpec
from cove.session_store.service import SessionStoreService


@dataclass
class HarnessInstance:
    session_id: str
    events: list[dict] = field(default_factory=list)
    sandbox_id: str | None = None
    max_turns: int = 50
    remaining_budget: float = 10.0
    turn: int = 0
    completed: bool = False


class SessionAlreadyCompleted(Exception):
    pass


class HarnessEngine:
    """Core inference loop — Cove's 'process scheduler'."""

    def __init__(
        self,
        session_store: SessionStoreService,
        sandbox_pool: SandboxPool,
        llm_client: LLMProvider,
        tool_router: ToolRouter | None = None,
        permission_system: PermissionSystem | None = None,
        context_builder: ContextBuilder | None = None,
    ):
        self.session_store = session_store
        self.sandbox_pool = sandbox_pool
        self.llm = llm_client
        self.tool_router = tool_router or ToolRouter(self.sandbox_pool)
        self.permissions = permission_system or PermissionSystem()
        self.context_builder = context_builder or ContextBuilder()

    async def wake(self, session_id: str) -> HarnessInstance:
        """Load a session and prepare for inference."""
        session = await self.session_store.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        if session.get("status") == "completed":
            raise SessionAlreadyCompleted(session_id)

        events = await self.session_store.get_events(session_id, limit=1000)
        config = session.get("config", {})

        sandbox_id = None
        if config.get("sandbox"):
            spec = SandboxSpec(
                image=config["sandbox"].get("image", "python:3.12-slim"),
                network=config["sandbox"].get("network", "restricted"),
            )
            instance = await self.sandbox_pool.provision(spec)
            sandbox_id = instance.id

        return HarnessInstance(
            session_id=session_id,
            events=events,
            sandbox_id=sandbox_id,
            max_turns=config.get("max_turns", 50),
            remaining_budget=config.get("max_budget_usd", 10.0),
        )

    async def loop(self, instance: HarnessInstance) -> AsyncIterator[dict]:
        """Main inference loop. Yields events as they are produced."""
        tools = self._get_tool_names()

        while instance.turn < instance.max_turns and instance.remaining_budget > 0:
            ctx = self.context_builder.build(instance.events, tool_names=tools)

            # System event: turn start
            yield {"type": "event", "event": {
                "kind": "system",
                "data": {"content": f"Turn {instance.turn + 1}"},
                "uuid": str(uuid.uuid4()),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }}

            full_response = ""
            async for chunk in self.llm.stream(
                system=ctx.system,
                messages=ctx.messages,
                tools=ctx.tools,
            ):
                if chunk.get("type") == "content_block_delta":
                    text = chunk.get("text", "")
                    full_response += text

            # Emit assistant message
            assistant_event = {
                "kind": "assistant_message",
                "data": {"content": full_response},
                "uuid": str(uuid.uuid4()),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            await self.session_store.emit_event(
                session_id=instance.session_id,
                kind=assistant_event["kind"],
                data=assistant_event["data"],
            )
            instance.events.append(assistant_event)
            yield {"type": "event", "event": assistant_event}

            # Check if we should stop (no tool calls expected in mock)
            instance.turn += 1
            # TODO: In production, parse tool_use from LLM response and route

        # Mark complete
        instance.completed = True
        if instance.sandbox_id:
            await self.sandbox_pool.destroy(instance.sandbox_id)

        yield {"type": "session_status", "status": "completed"}

    def _get_tool_names(self) -> list[str]:
        """Get list of available tool names based on permission mode."""
        if self.permissions.mode == "bypassPermissions":
            return ["Bash", "Read", "Edit", "WebSearch", "WebFetch"]
        return ["Read", "Edit", "Bash"]
