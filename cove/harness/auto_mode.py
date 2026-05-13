"""Simple auto-mode classifier for tool permission decisions."""

DANGEROUS_PATTERNS = [
    "rm -rf /", "sudo ", "chmod 777 ", "mkfs.", "dd if=", "> /dev/",
    "DROP TABLE", "DELETE FROM", "TRUNCATE ",
]

SAFE_COMMANDS = [
    "ls", "cat", "echo", "pwd", "cd", "git status", "git diff", "git log",
    "pip install", "npm install", "pytest", "python3", "python",
]


def classify_command(command: str) -> dict:
    """Classify a command as safe, dangerous, or unknown."""
    cmd_lower = command.lower().strip()

    for pattern in DANGEROUS_PATTERNS:
        if pattern in cmd_lower:
            return {"decision": "block", "reason": f"Command matches dangerous pattern: {pattern}"}

    for safe in SAFE_COMMANDS:
        if cmd_lower.startswith(safe):
            return {"decision": "allow", "reason": "Recognized safe command"}

    return {"decision": "ask", "reason": "Unknown command, requires approval"}
