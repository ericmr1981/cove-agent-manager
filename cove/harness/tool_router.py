from cove.sandbox.manager import SandboxPool


class ToolRouter:
    """Routes tool calls to the appropriate execution backend."""

    def __init__(self, sandbox_pool: SandboxPool):
        self.sandbox = sandbox_pool

    async def execute(self, tool_name: str, tool_input: dict, sandbox_id: str | None = None) -> dict:
        """Execute a tool call and return the result."""
        if tool_name == "Bash":
            return await self._exec_bash(tool_input, sandbox_id)
        elif tool_name == "Read":
            return await self._exec_read(tool_input, sandbox_id)
        elif tool_name == "Edit":
            return await self._exec_edit(tool_input, sandbox_id)
        elif tool_name == "WebSearch":
            return await self._exec_web_search(tool_input)
        elif tool_name == "WebFetch":
            return await self._exec_web_fetch(tool_input)
        else:
            return {"error": f"Unknown tool: {tool_name}"}

    async def _exec_bash(self, inp: dict, sandbox_id: str | None) -> dict:
        cmd = inp.get("command", "")
        if not sandbox_id:
            return {"content": f"[cove] sandbox not available, would run: {cmd}"}
        output = await self.sandbox.execute(sandbox_id, cmd)
        return {"content": output}

    async def _exec_read(self, inp: dict, sandbox_id: str | None) -> dict:
        path = inp.get("file_path", "")
        if not sandbox_id:
            return {"content": f"[cove] sandbox not available, would read: {path}"}
        output = await self.sandbox.execute(sandbox_id, f"cat {path}")
        return {"content": output}

    async def _exec_edit(self, inp: dict, sandbox_id: str | None) -> dict:
        path = inp.get("file_path", "")
        old = inp.get("old_string", "")
        new = inp.get("new_string", "")
        # Simple sed-based implementation for sandbox execution
        if not sandbox_id:
            return {"content": f"[cove] sandbox not available, would edit: {path}"}
        escaped_old = old.replace("'", "'\\''")
        escaped_new = new.replace("'", "'\\''")
        cmd = f"sed -i '' 's/{escaped_old}/{escaped_new}/g' {path}"
        output = await self.sandbox.execute(sandbox_id, cmd)
        return {"content": output or f"Edited {path}"}

    async def _exec_web_search(self, inp: dict) -> dict:
        return {"content": f"[cove] WebSearch requires MCP Proxy — would search: {inp.get('query', '')}"}

    async def _exec_web_fetch(self, inp: dict) -> dict:
        return {"content": f"[cove] WebFetch requires MCP Proxy — would fetch: {inp.get('url', '')}"}
