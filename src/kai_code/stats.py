from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class RunStats:
    started_ms: int
    ended_ms: int
    chunk_count: int = 0
    interrupted: bool = False

    # Tool usage metrics
    tool_call_count: int = 0
    tool_result_count: int = 0
    tool_error_count: int = 0
    tool_names: dict[str, int] = field(default_factory=dict)
    tool_latency_total_ms: int = 0
    tool_latency_max_ms: int = 0

    # Token usage metrics (mirrors UsageStats from stream_events.py)
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    cached_input_tokens: int | None = None
    reasoning_tokens: int | None = None

    # Timing and interaction metrics
    ttft_ms: int | None = None  # Time to first token
    message_count: int = 0
    turn_count: int = 0
    step_count: int = 0

    @property
    def duration_ms(self) -> int:
        return max(0, self.ended_ms - self.started_ms)

    def record_tool_call(self, name: str) -> None:
        """Record a tool call invocation.

        Increments the overall tool_call_count and tracks per-tool counts in tool_names.

        Args:
            name: The name of the tool being called.
        """
        self.tool_call_count += 1
        self.tool_names[name] = self.tool_names.get(name, 0) + 1

    def record_tool_result(
        self,
        name: str,
        latency_ms: int | None = None,
        is_error: bool = False,
    ) -> None:
        """Record a tool result.

        Increments tool_result_count and optionally tool_error_count.
        Updates latency metrics if latency_ms is provided.

        Args:
            name: The name of the tool that returned a result.
            latency_ms: Optional latency in milliseconds for this tool call.
            is_error: Whether this result represents an error.
        """
        self.tool_result_count += 1
        if is_error:
            self.tool_error_count += 1
        if latency_ms is not None:
            self.tool_latency_total_ms += latency_ms
            if latency_ms > self.tool_latency_max_ms:
                self.tool_latency_max_ms = latency_ms

    def add_token_usage(
        self,
        prompt: int | None = None,
        completion: int | None = None,
        total: int | None = None,
        cached: int | None = None,
        reasoning: int | None = None,
    ) -> None:
        """Add token usage metrics.

        Accumulates token counts by adding to existing values.
        None values are treated as 0 for accumulation purposes.

        Args:
            prompt: Prompt tokens to add.
            completion: Completion tokens to add.
            total: Total tokens to add.
            cached: Cached input tokens to add.
            reasoning: Reasoning tokens to add.
        """
        if prompt is not None:
            self.prompt_tokens = (self.prompt_tokens or 0) + prompt
        if completion is not None:
            self.completion_tokens = (self.completion_tokens or 0) + completion
        if total is not None:
            self.total_tokens = (self.total_tokens or 0) + total
        if cached is not None:
            self.cached_input_tokens = (self.cached_input_tokens or 0) + cached
        if reasoning is not None:
            self.reasoning_tokens = (self.reasoning_tokens or 0) + reasoning


def now_ms() -> int:
    return int(time.time() * 1000)

