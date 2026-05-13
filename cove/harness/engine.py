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

            # Accumulate chunks from LLM stream
            text_parts: list[str] = []
            tool_uses: list[dict] = []
            current_tool_use: dict | None = None

            async for chunk in self.llm.stream(
                system=ctx.system,
                messages=ctx.messages,
                tools=ctx.tools,
            ):
                chunk_type = chunk.get("type", "")

                if chunk_type == "content_block_delta":
                    text_parts.append(chunk.get("text", ""))

                elif chunk_type == "tool_use_start":
                    current_tool_use = {
                        "id": chunk.get("id", ""),
                        "name": chunk.get("name", ""),
                        "input": {},
                    }

                elif chunk_type == "tool_use_end":
                    if current_tool_use:
                        current_tool_use["input"] = chunk.get("input", {})
                        tool_uses.append(current_tool_use)
                        current_tool_use = None

            full_text = "".join(text_parts)

            # Emit assistant message (text portion, if any)
            if full_text.strip():
                assistant_event = {
                    "kind": "assistant_message",
                    "data": {"content": full_text},
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

            # Process tool_use blocks
            for tool_use in tool_uses:
                tool_name = tool_use.get("name", "")
                tool_input = tool_use.get("input", {})

                yield {"type": "event", "event": {
                    "kind": "tool_use",
                    "data": {"id": tool_use["id"], "name": tool_name, "input": tool_input},
                    "uuid": str(uuid.uuid4()),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }}

                # Check permissions
                decision = self.permissions.check(tool_name, tool_input)
                if not decision.allowed:
                    if decision.require_user_approval:
                        yield {"type": "permission_request", "tool": tool_name, "input": tool_input, "reason": decision.reason}
                        continue
                    yield {"type": "event", "event": {
                        "kind": "tool_error",
                        "data": {"content": f"Permission denied: {decision.reason}"},
                        "uuid": str(uuid.uuid4()),
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }}
                    continue

                # Execute tool
                result = await self.tool_router.execute(tool_name, tool_input, instance.sandbox_id)
                tool_result_event = {
                    "kind": "tool_result",
                    "data": {"content": result.get("content", ""), "tool_use_id": tool_use["id"]},
                    "uuid": str(uuid.uuid4()),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
                await self.session_store.emit_event(
                    session_id=instance.session_id,
                    kind=tool_result_event["kind"],
                    data=tool_result_event["data"],
                )
                instance.events.append(tool_result_event)
                yield {"type": "event", "event": tool_result_event}

            # If tool_use occurred, continue loop (LLM needs another turn with results)
            instance.turn += 1
            if tool_uses:
                continue

            # No tool_use — check if we should stop
            if not full_text.strip():
                break

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
