import asyncio
import tempfile
import uuid
from pathlib import Path

from cove.sandbox.providers.base import SandboxInstance


class LocalProvider:
    """Executes commands in a temp directory (for testing, no Docker required)."""

    def __init__(self):
        self._dirs: dict[str, Path] = {}

    async def create(self, spec) -> SandboxInstance:
        instance_id = str(uuid.uuid4())[:8]
        workdir = Path(tempfile.mkdtemp(prefix=f"cove-sandbox-{instance_id}-"))
        self._dirs[instance_id] = workdir
        return SandboxInstance(id=instance_id, image=spec.image, status="running")

    async def execute(self, instance: SandboxInstance, command: str) -> str:
        workdir = self._dirs.get(instance.id)
        if not workdir:
            raise ValueError(f"Sandbox {instance.id} not found")
        proc = await asyncio.create_subprocess_shell(
            command,
            cwd=str(workdir),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        output = stdout.decode() if stdout else ""
        error = stderr.decode() if stderr else ""
        if error:
            return f"STDERR:\n{error}\nSTDOUT:\n{output}"
        return output

    async def destroy(self, instance: SandboxInstance) -> None:
        workdir = self._dirs.pop(instance.id, None)
        if workdir and workdir.exists():
            import shutil
            shutil.rmtree(str(workdir))
