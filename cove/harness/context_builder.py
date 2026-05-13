from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

try:
    import tiktoken

    _ENCODING = tiktoken.encoding_for_model("gpt-4")
except ImportError:
    _ENCODING = None


@dataclass
class Context:
    system: str = ""
    messages: list[dict] = field(default_factory=list)
    tools: list[dict] = field(default_factory=list)
    total_tokens: int = 0


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
    """Builds LLM context from session events.

    Supports token estimation, compaction/trimming to fit within context windows,
    and configurable limits for production use.
    """

    MAX_CONTEXT_TOKENS = 128000

    def __init__(self, max_tokens: int = 128000, max_recent_events: int = 50):
        self.max_tokens = max_tokens
        self.max_recent_events = max_recent_events

    def build(self, events: list[dict], tool_names: list[str] | None = None) -> Context:
        """Build context from a list of session events."""
        tools = [t for t in TOOL_DEFINITIONS if tool_names is None or t["name"] in tool_names]

        # Compact events before converting to messages
        events = self._compact(events, self.max_tokens)

        messages = self._events_to_messages(events)

        # Estimate total token usage across the full context
        total_tokens = self._estimate_tokens(SYSTEM_PROMPT)
        for msg in messages:
            total_tokens += self._estimate_message_tokens(msg)
        for tool in tools:
            total_tokens += self._estimate_message_tokens(tool)

        return Context(
            system=SYSTEM_PROMPT,
            messages=messages,
            tools=tools,
            total_tokens=total_tokens,
        )

    # ------------------------------------------------------------------
    # Token estimation
    # ------------------------------------------------------------------

    def _estimate_tokens(self, text: str) -> int:
        """Estimate the number of tokens in *text*.

        Uses tiktoken (cl100k_base via gpt-4) when available, otherwise
        falls back to a rough ``len(text) // 4`` heuristic.
        """
        if not text:
            return 0
        if _ENCODING is not None:
            return len(_ENCODING.encode(text))
        # Rough estimate: ~4 chars/token for mixed Chinese/English
        return max(1, len(text) // 4)

    def _estimate_message_tokens(self, msg: dict) -> int:
        """Estimate the number of tokens in a single LLM message dict."""
        tokens = 0
        # Role overhead (role key + string + formatting)
        tokens += 4

        content = msg.get("content", "")
        if isinstance(content, str):
            tokens += self._estimate_tokens(content)
        elif isinstance(content, list):
            for block in content:
                for key in ("text", "name", "id", "tool_use_id", "content"):
                    val = block.get(key)
                    if val is not None:
                        tokens += self._estimate_tokens(str(val))
                inp = block.get("input")
                if inp is not None:
                    tokens += self._estimate_tokens(str(inp))
        return tokens

    def _estimate_event_tokens(self, event: dict) -> int:
        """Estimate the number of tokens contributed by a single session event."""
        kind = event.get("kind", "")
        data = event.get("data", {})
        tokens = 4  # overhead for kind + role

        if kind == "user_message":
            tokens += self._estimate_tokens(data.get("content", ""))
        elif kind == "assistant_message":
            tokens += self._estimate_tokens(data.get("content", ""))
        elif kind == "tool_use":
            tokens += self._estimate_tokens(data.get("name", ""))
            tokens += self._estimate_tokens(str(data.get("input", {})))
        elif kind == "tool_result":
            tokens += self._estimate_tokens(str(data.get("content", "")))

        return tokens

    # ------------------------------------------------------------------
    # Compaction
    # ------------------------------------------------------------------

    def _compact(self, events: list[dict], max_tokens: int) -> list[dict]:
        """Trim *events* to fit within *max_tokens*, keeping the most recent.

        * Keeps tool_use/tool_result pairs together (never splits a pair).
        * Never drops the last ``user_message`` event.
        * Older events that exceed the budget are replaced with a single
          ``system`` summary event.
        """
        if not events:
            return events

        total = sum(self._estimate_event_tokens(e) for e in events)
        if total <= max_tokens:
            return events

        # --- Build index of tool_use/tool_result pairs ------------------
        tu_id_to_idx: dict[str, int] = {}  # tool_use_id -> event index
        tr_idx_to_tu_id: dict[int, str] = {}  # event index -> tool_use_id

        for i, ev in enumerate(events):
            kind = ev.get("kind", "")
            data = ev.get("data", {})
            if kind == "tool_use":
                tu_id_to_idx[data.get("id", "")] = i
            elif kind == "tool_result":
                tr_idx_to_tu_id[i] = data.get("tool_use_id", "")

        # --- Locate the last user_message --------------------------------
        last_user_msg_idx = -1
        for i in range(len(events) - 1, -1, -1):
            if events[i].get("kind") == "user_message":
                last_user_msg_idx = i
                break

        # --- Walk from newest -> oldest to find the cutoff ---------------
        cumulative = 0
        cutoff = 0  # index of the first event to keep (inclusive)

        for i in range(len(events) - 1, -1, -1):
            tokens = self._estimate_event_tokens(events[i])
            if cumulative + tokens > max_tokens and i < len(events) - 1:
                # Events [0..i] are too old to keep — the cutoff starts at i+1
                cutoff = i + 1
                break
            cumulative += tokens
        else:
            # All events fit within the token budget (shouldn't reach here
            # since we checked total <= max_tokens above, but defensive).
            return events

        # --- Adjust for orphaned tool_results ---------------------------
        # If we keep a tool_result but its tool_use comes before the cutoff,
        # move the cutoff back to include the tool_use.
        for i in range(cutoff, len(events)):
            tu_id = tr_idx_to_tu_id.get(i)
            if tu_id is not None:
                tu_idx = tu_id_to_idx.get(tu_id)
                if tu_idx is not None and tu_idx < cutoff:
                    cutoff = tu_idx

        # --- Ensure the last user_message is never dropped ---------------
        if last_user_msg_idx >= 0 and last_user_msg_idx < cutoff:
            cutoff = last_user_msg_idx

        # --- Build the compacted event list ------------------------------
        if cutoff >= len(events):
            # Shouldn't happen, but be defensive
            return events

        if cutoff == 0:
            # Everything fits after adjustments
            return events

        kept_events = events[cutoff:]
        summary_event: dict[str, Any] = {
            "kind": "system",
            "data": {
                "content": (
                    "Earlier conversation history was compacted. "
                    "Summary: [system prompt would generate this in production]"
                ),
            },
        }
        return [summary_event] + kept_events

    # ------------------------------------------------------------------
    # Event → message conversion
    # ------------------------------------------------------------------

    def _events_to_messages(self, events: list[dict]) -> list[dict]:
        """Convert session events to LLM message format."""
        messages = []
        for event in events[-self.max_recent_events:]:
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
