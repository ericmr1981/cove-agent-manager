import asyncio
from dataclasses import dataclass, field
from typing import Any

from cove.sandbox.providers.base import SandboxProvider, SandboxInstance


@dataclass
class SandboxSpec:
    image: str = "python:3.12-slim"
    network: str = "isolated"
    timeout: int = 300
    env: dict[str, str] = field(default_factory=dict)
    mem_limit: str = "512m"
    cpu_limit: float = 1.0


class SandboxPool:
    """Manages a pool of Sandbox instances."""

    def __init__(self, provider: SandboxProvider, max_instances: int = 10):
        self.provider = provider
        self.max_instances = max_instances
        self._instances: dict[str, SandboxInstance] = {}

    async def provision(self, spec: SandboxSpec | None = None) -> SandboxInstance:
        if len(self._instances) >= self.max_instances:
            raise RuntimeError(f"Sandbox pool exhausted (max={self.max_instances})")
        spec = spec or SandboxSpec()
        instance = await self.provider.create(spec)
        self._instances[instance.id] = instance
        return instance

    async def execute(self, instance_id: str, command: str) -> str:
        instance = self._instances.get(instance_id)
        if not instance:
            raise ValueError(f"Sandbox {instance_id} not found")
        return await self.provider.execute(instance, command)

    async def destroy(self, instance_id: str) -> None:
        instance = self._instances.pop(instance_id, None)
        if instance:
            await self.provider.destroy(instance)

    async def destroy_all(self) -> None:
        for instance_id in list(self._instances.keys()):
            await self.destroy(instance_id)
