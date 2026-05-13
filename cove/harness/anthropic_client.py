import json
from collections.abc import AsyncIterator

from anthropic import AsyncAnthropic


class AnthropicClient:
    """Real Anthropic API client for Cove harness."""

    def __init__(self, api_key: str | None = None, model: str = "claude-sonnet-4-20250514"):
        self.client = AsyncAnthropic(api_key=api_key)
        self.model = model

    async def stream(
        self,
        system: str,
        messages: list[dict],
        tools: list[dict] | None = None,
        max_tokens: int = 4096,
    ) -> AsyncIterator[dict]:
        kwargs = dict(
            model=self.model,
            system=system,
            messages=messages,
            max_tokens=max_tokens,
        )
        if tools:
            kwargs["tools"] = tools

        async with self.client.messages.stream(**kwargs) as stream:
            tool_input_chunks: dict[str, list[str]] = {}
            tool_name: str | None = None
            tool_id: str | None = None
            current_tool_index: int | None = None

            async for event in stream:
                if event.type == "content_block_start":
                    block = event.content_block
                    if block.type == "tool_use":
                        tool_name = block.name
                        tool_id = block.id
                        current_tool_index = event.index
                        tool_input_chunks[tool_id] = []
                        yield {
                            "type": "tool_use_start",
                            "id": tool_id,
                            "name": tool_name,
                            "index": event.index,
                        }
                    elif block.type == "text":
                        yield {"type": "text_start", "index": event.index}

                elif event.type == "content_block_delta":
                    delta = event.delta
                    if delta.type == "text_delta":
                        yield {"type": "content_block_delta", "text": delta.text}
                    elif delta.type == "input_json_delta" and tool_id:
                        tool_input_chunks[tool_id].append(delta.partial_json)

                elif event.type == "content_block_stop":
                    if tool_id and tool_id in tool_input_chunks:
                        raw = "".join(tool_input_chunks[tool_id])
                        try:
                            tool_input = json.loads(raw)
                        except (json.JSONDecodeError, ValueError):
                            tool_input = {}
                        yield {
                            "type": "tool_use_end",
                            "id": tool_id,
                            "name": tool_name,
                            "input": tool_input,
                        }
                        tool_id = None
                        tool_name = None
                        current_tool_index = None
