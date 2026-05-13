import httpx


class MCPProxy:
    """Proxies MCP (Model Context Protocol) server requests with credential injection."""

    def __init__(self, vault: "CredentialVault" = None):  # noqa: F821
        from cove.security.vault import CredentialVault
        self.vault = vault or CredentialVault()
        self._client = httpx.AsyncClient(timeout=30)

    async def call_tool(self, server_url: str, tool_name: str, args: dict) -> dict:
        """Call an MCP tool with injected credentials."""
        headers = {}
        cred_key = f"mcp:{server_url}:token"
        token = self.vault.get(cred_key)
        if token:
            headers["Authorization"] = f"Bearer {token}"

        try:
            resp = await self._client.post(
                f"{server_url}/mcp/tool/{tool_name}",
                json=args,
                headers=headers,
            )
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            return {"error": f"MCP call failed: {e.response.status_code}"}
        except httpx.RequestError as e:
            return {"error": f"MCP connection failed: {str(e)}"}

    async def close(self):
        await self._client.aclose()
