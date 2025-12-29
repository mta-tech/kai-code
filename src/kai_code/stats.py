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


def now_ms() -> int:
    return int(time.time() * 1000)

