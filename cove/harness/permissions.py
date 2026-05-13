from dataclasses import dataclass


@dataclass
class PermissionDecision:
    allowed: bool
    reason: str = ""
    require_user_approval: bool = False


class PermissionSystem:
    """Controls tool execution permissions."""

    DANGEROUS_PATTERNS: dict[str, list[str]] = {
        "Bash": ["rm -rf", "sudo", "chmod 777", "mkfs", "dd if="],
        "WebFetch": ["file://", "127.0.0.1", "localhost"],
    }

    def __init__(self, mode: str = "acceptEdits"):
        self.mode = mode

    def check(self, tool_name: str, tool_input: dict) -> PermissionDecision:
        """Check if a tool call should be allowed."""
        if self.mode == "bypassPermissions":
            return PermissionDecision(allowed=True)

        if tool_name in ("Read", "Grep", "Glob"):
            return PermissionDecision(allowed=True)

        if tool_name == "Edit" and self.mode == "acceptEdits":
            return PermissionDecision(allowed=True)

        if self._is_dangerous(tool_name, tool_input):
            return PermissionDecision(
                allowed=False,
                reason=f"Dangerous tool '{tool_name}' requires user approval",
                require_user_approval=True,
            )

        if self.mode == "auto":
            return PermissionDecision(
                allowed=False,
                require_user_approval=True,
                reason=f"Tool '{tool_name}' requires approval in auto mode",
            )

        return PermissionDecision(allowed=True)

    def _is_dangerous(self, tool_name: str, tool_input: dict) -> bool:
        patterns = self.DANGEROUS_PATTERNS.get(tool_name, [])
        command = str(tool_input).lower()
        return any(p in command for p in patterns)
