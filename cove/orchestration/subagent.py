import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

from cove.harness.engine import HarnessEngine
from cove.harness.mock_client import MockLLMClient
from cove.sandbox.manager import SandboxPool
from cove.session_store.service import SessionStoreService


@dataclass
class SubAgentTask:
    id: str = ""
    name: str = ""
    status: str = "pending"  # pending | running | completed | failed
    result: str = ""
    error: str = ""


class SubAgentOrchestrator:
    """Manages parallel Sub-Agent execution."""

    def __init__(self, session_store: SessionStoreService, sandbox_pool: SandboxPool):
        self.store = session_store
        self.sandbox = sandbox_pool

    async def run_parallel(self, tasks: list[SubAgentTask]) -> list[SubAgentTask]:
        """Run multiple sub-agent tasks in parallel."""
        async def run_one(task: SubAgentTask) -> SubAgentTask:
            task.id = str(uuid.uuid4())[:8]
            task.status = "running"
            try:
                session = await self.store.create_session(f"sub-{task.name}")
                engine = HarnessEngine(
                    session_store=self.store,
                    sandbox_pool=self.sandbox,
                    llm_client=MockLLMClient(),
                )
                inst = await engine.wake(session["session_id"])
                async for event in engine.loop(inst):
                    if event.get("type") == "event":
                        ev = event["event"]
                        if ev["kind"] == "assistant_message":
                            task.result += ev["data"].get("content", "")
                task.status = "completed"
            except Exception as e:
                task.status = "failed"
                task.error = str(e)
            return task

        results = await asyncio.gather(*[run_one(t) for t in tasks], return_exceptions=False)
        return list(results)

    async def run_sequential(self, tasks: list[SubAgentTask]) -> list[SubAgentTask]:
        results = []
        for task in tasks:
            result = await self.run_parallel([task])
            results.append(result[0])
        return results
