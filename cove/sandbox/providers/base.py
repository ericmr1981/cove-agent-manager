from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from cove.sandbox.manager import SandboxSpec


@dataclass
class SandboxInstance:
    id: str
    image: str
    status: str = "created"


class SandboxProvider(Protocol):
    async def create(self, spec: "SandboxSpec") -> SandboxInstance: ...
    async def execute(self, instance: SandboxInstance, command: str) -> str: ...
    async def destroy(self, instance: SandboxInstance) -> None: ...
