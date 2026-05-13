"""Tests for the ContextBuilder compaction and token estimation."""

import pytest

from cove.harness.context_builder import ContextBuilder, SYSTEM_PROMPT


# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------

@pytest.fixture
def builder():
    return ContextBuilder()


@pytest.fixture
def short_builder():
    """A builder with a tiny token budget to force compaction."""
    return ContextBuilder(max_tokens=200, max_recent_events=100)


@pytest.fixture
def many_events():
    """Generate enough events to trigger compaction (~1.5k tokens)."""
    events = []
    # 10 exchanges each with a short user message + short assistant reply
    for i in range(10):
        events.append({
            "kind": "user_message",
            "data": {"content": f"Hello from turn {i}"},
        })
        events.append({
            "kind": "assistant_message",
            "data": {"content": f"Response for turn {i}"},
        })
    return events


# ------------------------------------------------------------------
# Basic context building
# ------------------------------------------------------------------

class TestBuildBasic:
    def test_build_returns_context(self, builder):
        events = [
            {"kind": "user_message", "data": {"content": "Hello"}},
            {"kind": "assistant_message", "data": {"content": "Hi there"}},
        ]
        ctx = builder.build(events)
        assert ctx.system == SYSTEM_PROMPT
        assert len(ctx.messages) == 2
        assert ctx.messages[0]["role"] == "user"
        assert ctx.messages[0]["content"] == "Hello"
        assert ctx.messages[1]["role"] == "assistant"
        assert ctx.messages[1]["content"] == "Hi there"
        assert ctx.total_tokens > 0

    def test_build_empty_events(self, builder):
        ctx = builder.build([])
        assert ctx.messages == []
        assert ctx.total_tokens > 0  # system prompt always counted

    def test_build_with_tool_filtering(self, builder):
        events = [
            {"kind": "user_message", "data": {"content": "Run a command"}},
            {"kind": "tool_use", "data": {
                "id": "tu1", "name": "Bash", "input": {"command": "ls"},
            }},
            {"kind": "tool_result", "data": {
                "tool_use_id": "tu1", "content": "file1.txt",
            }},
        ]
        ctx = builder.build(events, tool_names=["Read", "Edit"])
        assert len(ctx.tools) == 2
        assert ctx.tools[0]["name"] == "Read"
        assert ctx.tools[1]["name"] == "Edit"

    def test_build_converts_tool_events(self, builder):
        events = [
            {"kind": "user_message", "data": {"content": "Do something"}},
            {"kind": "tool_use", "data": {
                "id": "tu1", "name": "Bash", "input": {"command": "ls"},
            }},
            {"kind": "tool_result", "data": {
                "tool_use_id": "tu1", "content": "file1.txt",
            }},
        ]
        ctx = builder.build(events)
        assert len(ctx.messages) == 3
        assert ctx.messages[0]["role"] == "user"
        assert ctx.messages[1]["role"] == "assistant"
        assert ctx.messages[1]["content"][0]["type"] == "tool_use"
        assert ctx.messages[2]["role"] == "user"
        assert ctx.messages[2]["content"][0]["type"] == "tool_result"

    def test_total_tokens_increases_with_messages(self, builder):
        ctx_empty = builder.build([])
        ctx_full = builder.build([
            {"kind": "user_message", "data": {"content": "Hello world " * 50}},
            {"kind": "assistant_message", "data": {"content": "Response text " * 50}},
        ])
        assert ctx_full.total_tokens > ctx_empty.total_tokens


# ------------------------------------------------------------------
# Token estimation
# ------------------------------------------------------------------

class TestTokenEstimation:
    def test_estimate_empty_string(self, builder):
        assert builder._estimate_tokens("") == 0
        assert builder._estimate_tokens(None) == 0

    def test_estimate_short_text(self, builder):
        tokens = builder._estimate_tokens("Hello")
        assert 1 <= tokens <= 3

    def test_estimate_longer_text(self, builder):
        text = "Hello world, this is a test message. " * 20
        tokens = builder._estimate_tokens(text)
        assert tokens > 5

    def test_estimate_chinese_text(self, builder):
        text = "你好世界，这是一个测试消息。" * 10
        tokens = builder._estimate_tokens(text)
        # Chinese chars are ~2-3 chars/token with cl100k, 4 chars/token fallback
        assert tokens >= 1

    def test_estimate_message_tokens_string_content(self, builder):
        msg = {"role": "user", "content": "Hello world"}
        tokens = builder._estimate_message_tokens(msg)
        assert tokens >= 4  # at least the role overhead

    def test_estimate_message_tokens_list_content(self, builder):
        msg = {
            "role": "assistant",
            "content": [
                {"type": "tool_use", "id": "tu1", "name": "Bash", "input": {"cmd": "ls"}},
            ],
        }
        tokens = builder._estimate_message_tokens(msg)
        assert tokens >= 4

    def test_estimate_message_tokens_empty(self, builder):
        msg = {"role": "user", "content": ""}
        tokens = builder._estimate_message_tokens(msg)
        assert tokens == 4  # just the role overhead


# ------------------------------------------------------------------
# Compaction basics
# ------------------------------------------------------------------

class TestCompactionBasic:
    def test_no_compaction_when_under_budget(self, builder, many_events):
        """With default 128k tokens, 10 short exchanges should not be compacted."""
        compacted = builder._compact(many_events, builder.max_tokens)
        assert len(compacted) == len(many_events)
        # All original events present (no summary)
        assert compacted[0]["kind"] == "user_message"

    def test_compaction_drops_old_events(self, short_builder):
        """With a very small token budget, old events get replaced by summary."""
        # Each event: 300 char content ~75 content tokens + 4 overhead = ~79 tokens
        # 7 events * 79 = ~553 total >> 200 max_tokens
        events = [
            {"kind": "user_message", "data": {"content": "A" * 300}},
            {"kind": "assistant_message", "data": {"content": "B" * 300}},
            {"kind": "user_message", "data": {"content": "C" * 300}},
            {"kind": "assistant_message", "data": {"content": "D" * 300}},
            {"kind": "user_message", "data": {"content": "E" * 300}},
            {"kind": "assistant_message", "data": {"content": "F" * 300}},
            {"kind": "user_message", "data": {"content": "Hello"}},
        ]
        compacted = short_builder._compact(events, short_builder.max_tokens)
        # Should have summary + some kept events
        assert compacted[0]["kind"] == "system"
        assert "compacted" in compacted[0]["data"]["content"]
        assert len(compacted) < len(events)

    def test_compaction_summary_content(self, short_builder):
        # Large event (~1250 content tokens + 4 overhead = ~1254 tokens) + small event (~5 tokens)
        # = ~1259 total >> 200 max_tokens — with tiktoken, repetitive chars tokenize efficiently
        events = [
            {"kind": "user_message", "data": {"content": "X" * 10000}},
            {"kind": "user_message", "data": {"content": "Y"}},
        ]
        compacted = short_builder._compact(events, short_builder.max_tokens)
        assert compacted[0]["kind"] == "system"
        assert "compacted" in compacted[0]["data"]["content"]

    def test_compaction_no_events(self, builder):
        assert builder._compact([], builder.max_tokens) == []

    def test_compaction_single_event(self, builder):
        events = [{"kind": "user_message", "data": {"content": "Hi"}}]
        compacted = builder._compact(events, builder.max_tokens)
        assert compacted == events

    def test_compaction_preserves_tool_pairs(self, builder):
        """tool_use + tool_result pairs must not be split by compaction."""
        events = [
            {"kind": "user_message", "data": {"content": "A" * 1000}},
            {"kind": "tool_use", "data": {
                "id": "tu_save", "name": "Bash", "input": {"cmd": "echo hi"},
            }},
            {"kind": "tool_result", "data": {
                "tool_use_id": "tu_save", "content": "hi",
            }},
        ]
        # Max tokens just enough for one exchange but not the first user msg
        compacted = builder._compact(events, max_tokens=1000)
        # Both tool_use and tool_result should be present if either is kept
        kinds = [e["kind"] for e in compacted]
        if "tool_use" in kinds:
            assert "tool_result" in kinds

    def test_compaction_merges_older_recent(self, short_builder, many_events):
        """Old events are merged into the summary; recent events stay."""
        # many_events has 20 short events (~5 tokens each). Use a tiny budget
        # so compaction is triggered.
        tiny = ContextBuilder(max_tokens=60, max_recent_events=100)
        compacted = tiny._compact(many_events, tiny.max_tokens)
        # There should be a summary event at the front
        assert compacted[0]["kind"] == "system"
        # At least some events should remain after the summary
        assert len(compacted) > 1


# ------------------------------------------------------------------
# Last user_message preservation
# ------------------------------------------------------------------

class TestCompactionKeepsLastUserMessage:
    def test_last_user_message_always_kept(self, short_builder):
        """Even with extreme compaction, the last user_message survives."""
        events = [
            {"kind": "user_message", "data": {"content": "A" * 500}},
            {"kind": "assistant_message", "data": {"content": "B" * 500}},
            {"kind": "user_message", "data": {"content": "LAST_MESSAGE"}},
        ]
        compacted = short_builder._compact(events, short_builder.max_tokens)
        # Find the last user_message
        user_msgs = [e for e in compacted if e["kind"] == "user_message"]
        assert len(user_msgs) >= 1
        assert user_msgs[-1]["data"]["content"] == "LAST_MESSAGE"

    def test_last_user_message_not_buried_in_summary(self, short_builder):
        """The last user_message should appear as a distinct event, not in summary."""
        events = [
            {"kind": "user_message", "data": {"content": "X" * 5000}},
            {"kind": "assistant_message", "data": {"content": "Y" * 5000}},
            {"kind": "user_message", "data": {"content": "Final question"}},
        ]
        compacted = short_builder._compact(events, short_builder.max_tokens)
        # The last event should be the final user_message
        assert compacted[-1]["kind"] == "user_message"
        assert compacted[-1]["data"]["content"] == "Final question"

    def test_single_user_message_kept(self, short_builder):
        """A single user_message is never compacted away."""
        events = [
            {"kind": "user_message", "data": {"content": "Hello " * 100}},
        ]
        compacted = short_builder._compact(events, short_builder.max_tokens)
        assert any(e["kind"] == "user_message" for e in compacted)


# ------------------------------------------------------------------
# Custom max_tokens
# ------------------------------------------------------------------

class TestCustomMaxTokens:
    def test_custom_max_tokens_in_build(self):
        """Custom max_tokens affects whether compaction triggers."""
        tiny = ContextBuilder(max_tokens=50, max_recent_events=100)
        events = [
            {"kind": "user_message", "data": {"content": "Hello world " * 20}},
            {"kind": "assistant_message", "data": {"content": "Response text " * 20}},
        ]
        ctx = tiny.build(events)
        # Compaction should have triggered
        assert ctx.total_tokens <= tiny.max_tokens + 500  # Allow slack

    def test_custom_large_max_tokens_no_compaction(self):
        """Huge max_tokens means no compaction is needed."""
        huge = ContextBuilder(max_tokens=1_000_000, max_recent_events=100)
        events = [
            {"kind": "user_message", "data": {"content": "Hello"}},
            {"kind": "user_message", "data": {"content": "World"}},
        ]
        compacted = huge._compact(events, huge.max_tokens)
        assert len(compacted) == len(events)
        assert compacted[0]["kind"] == "user_message"

    def test_max_recent_events_limits_messages(self):
        """max_recent_events caps how many events become messages."""
        limited = ContextBuilder(max_tokens=1_000_000, max_recent_events=2)
        events = [
            {"kind": "user_message", "data": {"content": "A"}},
            {"kind": "user_message", "data": {"content": "B"}},
            {"kind": "user_message", "data": {"content": "C"}},
        ]
        ctx = limited.build(events)
        assert len(ctx.messages) == 2
        assert ctx.messages[0]["content"] == "B"
        assert ctx.messages[1]["content"] == "C"

    def test_compaction_with_custom_limit(self):
        """Custom max_tokens triggers compaction at the right threshold."""
        # 3 events with large content easily exceed 150 tokens total
        custom = ContextBuilder(max_tokens=150, max_recent_events=100)
        events = [
            {"kind": "user_message", "data": {"content": "A" * 400}},
            {"kind": "assistant_message", "data": {"content": "B" * 400}},
            {"kind": "user_message", "data": {"content": "C"}},
        ]
        compacted = custom._compact(events, custom.max_tokens)
        assert compacted[0]["kind"] == "system"


# ------------------------------------------------------------------
# Integration: build() end-to-end with compaction
# ------------------------------------------------------------------

class TestBuildWithCompaction:
    def test_build_compacts_over_budget(self):
        """build() should call _compact() and produce a limited context."""
        tight = ContextBuilder(max_tokens=200, max_recent_events=100)
        events = [
            {"kind": "user_message", "data": {"content": "X" * 200}},
            {"kind": "assistant_message", "data": {"content": "Y" * 200}},
            {"kind": "user_message", "data": {"content": "Final ping"}},
        ]
        ctx = tight.build(events)
        # The last user_message should always be present
        assert any(m["role"] == "user" and "Final ping" in str(m["content"])
                   for m in ctx.messages)
        assert ctx.total_tokens > 0
