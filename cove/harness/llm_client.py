from collections.abc import AsyncIterator
from typing import Protocol


class LLMProvider(Protocol):
    """Protocol for LLM providers (Claude, mock, etc.)."""

    async def stream(
        self,
        system: str,
        messages: list[dict],
        tools: list[dict] | None = None,
        max_tokens: int = 4096,
    ) -> AsyncIterator[dict]:
        ...
