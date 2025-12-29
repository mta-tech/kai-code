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

    def to_dict(self) -> dict:
        """Return a clean dict representation for JSON output.

        The structure is compatible with the existing CLI stats format used
        in stream-json output. Token usage is nested under a 'token_usage' key.

        Returns:
            A dictionary with all stats fields, ready for JSON serialization.
        """
        # Calculate average latency if we have tool results
        tool_latency_ms_avg: float | None = None
        if self.tool_result_count > 0 and self.tool_latency_total_ms > 0:
            tool_latency_ms_avg = self.tool_latency_total_ms / self.tool_result_count

        return {
            "duration_ms": self.duration_ms,
            "started_ms": self.started_ms,
            "ended_ms": self.ended_ms,
            "ttft_ms": self.ttft_ms,
            "chunk_count": self.chunk_count,
            "interrupted": self.interrupted,
            "message_count": self.message_count,
            "turn_count": self.turn_count,
            "step_count": self.step_count,
            "tool_call_count": self.tool_call_count,
            "tool_result_count": self.tool_result_count,
            "tool_error_count": self.tool_error_count,
            "tool_count": len(self.tool_names),
            "tool_names": dict(self.tool_names) if self.tool_names else {},
            "tool_latency_ms_total": self.tool_latency_total_ms,
            "tool_latency_ms_avg": tool_latency_ms_avg,
            "tool_latency_ms_max": self.tool_latency_max_ms if self.tool_latency_max_ms > 0 else None,
            "token_usage": {
                "prompt_tokens": self.prompt_tokens,
                "completion_tokens": self.completion_tokens,
                "total_tokens": self.total_tokens,
                "cached_input_tokens": self.cached_input_tokens,
                "reasoning_tokens": self.reasoning_tokens,
            },
        }


def now_ms() -> int:
    return int(time.time() * 1000)


class RunStatsCollector:
    """Context manager for collecting metrics during agent.stream() iteration.

    This helper class wraps the stream iteration loop and automatically collects
    timing, tool usage, and token metrics. It handles deduplication of tool events
    and latency tracking internally.

    Usage:
        with RunStatsCollector() as collector:
            for chunk in agent.stream(prompt):
                collector.observe_chunk(chunk)
            # Get the final stats
            stats = collector.stats

    The collector can also be used without the context manager pattern:
        collector = RunStatsCollector()
        collector.start()
        for chunk in agent.stream(prompt):
            collector.observe_chunk(chunk)
        collector.finish()
        stats = collector.stats
    """

    def __init__(self) -> None:
        self._stats = RunStats(started_ms=0, ended_ms=0)
        self._tool_call_started_ms: dict[str, int] = {}
        self._seen_tool_calls: set[str] = set()
        self._seen_tool_results: set[str] = set()
        self._last_snapshot: dict | None = None
        self._started = False

    @property
    def stats(self) -> RunStats:
        """Get the collected RunStats instance."""
        return self._stats

    @property
    def last_snapshot(self) -> dict | None:
        """Get the last observed snapshot containing messages."""
        return self._last_snapshot

    def start(self) -> None:
        """Start timing. Called automatically by __enter__."""
        self._stats.started_ms = now_ms()
        self._started = True

    def finish(self) -> None:
        """Finish timing and finalize stats. Called automatically by __exit__."""
        self._stats.ended_ms = now_ms()

        # Process final snapshot for aggregated metrics (token usage, turn/step counts)
        if self._last_snapshot is not None:
            self._process_final_snapshot(self._last_snapshot)

    def __enter__(self) -> "RunStatsCollector":
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        self.finish()
        return False

    def observe_chunk(self, chunk) -> list:
        """Observe a streaming chunk and collect metrics.

        Records timing metrics (ttft_ms, chunk_count) and extracts tool events
        from message snapshots. Returns a list of newly observed ToolEvent objects
        for the caller to process (e.g., for emitting JSON events).

        Args:
            chunk: A streaming chunk from agent.stream(). Expected to be a dict
                   with an optional "messages" list.

        Returns:
            A list of tuples (event_type, tool_event, extra_info) where:
            - event_type is "tool_call" or "tool_result"
            - tool_event is the ToolEvent object
            - extra_info is a dict with additional data like latency_ms, is_error
        """
        if not self._started:
            self.start()

        ts_ms = now_ms()
        self._stats.chunk_count += 1

        # Record time to first token
        if self._stats.ttft_ms is None:
            self._stats.ttft_ms = max(0, ts_ms - self._stats.started_ms)

        # Check for interrupt
        if isinstance(chunk, dict) and chunk.get("__interrupt__"):
            self._stats.interrupted = True
            return []

        # Process message snapshots
        new_events = []
        if isinstance(chunk, dict) and isinstance(chunk.get("messages"), list):
            self._last_snapshot = chunk
            messages = chunk.get("messages")

            # Import here to avoid circular imports
            from .stream_events import (
                correlate_tool_events,
                count_turns_steps,
                detect_tool_events_from_messages,
                extract_tool_result_fields,
                synthesize_tool_call_id,
            )

            # Get turn/step for correlation
            turns, steps = count_turns_steps(messages)
            turn_id = (turns - 1) if isinstance(turns, int) and turns > 0 else None
            step_id = (steps - 1) if isinstance(steps, int) and steps > 0 else None

            # Extract and correlate tool events
            tool_events = correlate_tool_events(
                detect_tool_events_from_messages(messages),
                turn_id=turn_id,
                step_id=step_id,
            )

            for te in tool_events:
                if te.kind == "tool_call":
                    tc_id = te.tool_call_id or synthesize_tool_call_id(
                        te, turn_id=turn_id, step_id=step_id
                    )
                    key = tc_id or f"{te.tool_name}:{te.args}"
                    if key in self._seen_tool_calls:
                        continue
                    self._seen_tool_calls.add(key)

                    # Record tool call in RunStats
                    self._stats.record_tool_call(te.tool_name)

                    # Track start time for latency calculation
                    if tc_id is not None:
                        self._tool_call_started_ms[tc_id] = ts_ms

                    new_events.append((
                        "tool_call",
                        te,
                        {"turn_id": turn_id, "step_id": step_id, "tool_call_id": tc_id},
                    ))

                elif te.kind == "tool_result":
                    tr_id = te.tool_call_id or synthesize_tool_call_id(
                        te, turn_id=turn_id, step_id=step_id
                    )
                    key = tr_id or f"{te.tool_name}:{te.content}"
                    if key in self._seen_tool_results:
                        continue
                    self._seen_tool_results.add(key)

                    # Calculate latency
                    tool_latency_ms = None
                    if tr_id is not None and tr_id in self._tool_call_started_ms:
                        tool_latency_ms = max(0, ts_ms - self._tool_call_started_ms[tr_id])

                    # Detect if this is an error result
                    result_fields = extract_tool_result_fields(te)
                    is_error = (
                        result_fields.get("status") == "error"
                        or (
                            result_fields.get("exit_code") is not None
                            and result_fields.get("exit_code") != 0
                        )
                    )

                    # Record tool result in RunStats
                    self._stats.record_tool_result(
                        te.tool_name or "",
                        latency_ms=tool_latency_ms,
                        is_error=is_error,
                    )

                    new_events.append((
                        "tool_result",
                        te,
                        {
                            "turn_id": turn_id,
                            "step_id": step_id,
                            "tool_call_id": tr_id,
                            "latency_ms": tool_latency_ms,
                            "is_error": is_error,
                            "result_fields": result_fields,
                        },
                    ))

        return new_events

    def _process_final_snapshot(self, snapshot: dict) -> None:
        """Process the final snapshot to extract aggregated metrics."""
        from .stream_events import aggregate_usage, count_turns_steps

        messages = snapshot.get("messages")
        if not isinstance(messages, list):
            return

        self._stats.message_count = len(messages)
        turns, steps = count_turns_steps(messages)
        self._stats.turn_count = turns or 0
        self._stats.step_count = steps or 0

        # Aggregate token usage
        u_total = aggregate_usage(messages)
        self._stats.add_token_usage(
            prompt=u_total.prompt_tokens,
            completion=u_total.completion_tokens,
            total=u_total.total_tokens,
            cached=u_total.cached_input_tokens,
            reasoning=u_total.reasoning_tokens,
        )

    def get_tool_call_ids(self) -> set[str]:
        """Get the set of observed tool call IDs."""
        return set(self._seen_tool_calls)

    def get_tool_result_ids(self) -> set[str]:
        """Get the set of observed tool result IDs."""
        return set(self._seen_tool_results)

    def get_tool_call_start_time(self, tool_call_id: str) -> int | None:
        """Get the start timestamp for a tool call by ID."""
        return self._tool_call_started_ms.get(tool_call_id)
