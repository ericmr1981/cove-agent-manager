from collections.abc import AsyncIterator


class MockLLMClient:
    """Mock LLM for testing — returns predefined responses."""

    def __init__(self, responses: list[list[dict]] | None = None):
        self.responses = responses or [
            [{"type": "content_block_delta", "text": "Hello from Cove!"}],
        ]
        self.call_count = 0

    async def stream(
        self,
        system: str = "",
        messages: list[dict] | None = None,
        tools: list[dict] | None = None,
        max_tokens: int = 4096,
    ) -> AsyncIterator[dict]:
        if self.call_count < len(self.responses):
            for chunk in self.responses[self.call_count]:
                yield chunk
            self.call_count += 1
