from dataclasses import dataclass, field


@dataclass
class Context:
    system: str = ""
    messages: list[dict] = field(default_factory=list)
    tools: list[dict] = field(default_factory=list)


SYSTEM_PROMPT = """You are Cove, an AI agent operating in a sandboxed environment.
You have access to tools for reading, writing, and executing code.
Always respond in Chinese when the user writes in Chinese."""

TOOL_DEFINITIONS = [
    {
        "name": "Bash",
        "description": "Execute a shell command in the sandbox",
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "Shell command to execute"},
            },
            "required": ["command"],
        },
    },
    {
        "name": "Read",
        "description": "Read a file from the sandbox",
        "input_schema": {
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "Path to the file"},
            },
            "required": ["file_path"],
        },
    },
    {
        "name": "Edit",
        "description": "Edit a file in the sandbox",
        "input_schema": {
            "type": "object",
            "properties": {
                "file_path": {"type": "string"},
                "old_string": {"type": "string"},
                "new_string": {"type": "string"},
            },
            "required": ["file_path", "old_string", "new_string"],
        },
    },
    {
        "name": "WebSearch",
        "description": "Search the web",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "WebFetch",
        "description": "Fetch a URL",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {"type": "string"},
            },
            "required": ["url"],
        },
    },
]


class ContextBuilder:
    """Builds LLM context from session events."""

    MAX_RECENT_EVENTS = 50

    def build(self, events: list[dict], tool_names: list[str] | None = None) -> Context:
        """Build context from a list of session events."""
        tools = [t for t in TOOL_DEFINITIONS if tool_names is None or t["name"] in tool_names]

        messages = self._events_to_messages(events)

        return Context(
            system=SYSTEM_PROMPT,
            messages=messages,
            tools=tools,
        )

    def _events_to_messages(self, events: list[dict]) -> list[dict]:
        """Convert session events to LLM message format."""
        messages = []
        for event in events[-self.MAX_RECENT_EVENTS:]:
            kind = event.get("kind", "")
            data = event.get("data", {})

            if kind == "user_message":
                messages.append({"role": "user", "content": data.get("content", "")})
            elif kind == "assistant_message":
                messages.append({"role": "assistant", "content": data.get("content", "")})
            elif kind == "tool_use":
                messages.append({
                    "role": "assistant",
                    "content": [
                        {
                            "type": "tool_use",
                            "id": data.get("id", ""),
                            "name": data.get("name", ""),
                            "input": data.get("input", {}),
                        }
                    ],
                })
            elif kind == "tool_result":
                if messages and messages[-1].get("role") == "user":
                    messages[-1]["content"] += [
                        {
                            "type": "tool_result",
                            "tool_use_id": data.get("tool_use_id", ""),
                            "content": data.get("content", ""),
                        }
                    ]
                else:
                    messages.append({
                        "role": "user",
                        "content": [
                            {
                                "type": "tool_result",
                                "tool_use_id": data.get("tool_use_id", ""),
                                "content": data.get("content", ""),
                            }
                        ],
                    })

        return messages
