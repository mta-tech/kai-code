from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

# Import modules directly to avoid triggering kai_code/__init__.py (which has deps)
_src_dir = Path(__file__).parent.parent / "src" / "kai_code"


def _load_module(name: str, path: Path):
    """Load a module directly from file path."""
    spec = importlib.util.spec_from_file_location(f"kai_code.{name}", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[f"kai_code.{name}"] = module
    spec.loader.exec_module(module)
    return module


# Load stream_events first (stats depends on it in RunStatsCollector)
_stream_events = _load_module("stream_events", _src_dir / "stream_events.py")
aggregate_usage = _stream_events.aggregate_usage
count_turns_steps = _stream_events.count_turns_steps
last_stop_reason = _stream_events.last_stop_reason

# Load stats module
_stats = _load_module("stats", _src_dir / "stats.py")
RunStats = _stats.RunStats
RunStatsCollector = _stats.RunStatsCollector
now_ms = _stats.now_ms


def main() -> int:
    # -------------------------------------------------------------------------
    # Part 1: Basic stream_events helpers (original functionality)
    # -------------------------------------------------------------------------
    msgs = [
        {"role": "user", "content": "hi"},
        {
            "role": "assistant",
            "content": "ok",
            "response_metadata": {"stop_reason": "end_turn"},
            "usage_metadata": {"input_tokens": 3, "output_tokens": 5, "total_tokens": 8},
        },
        {
            "role": "assistant",
            "content": "more",
            "usage_metadata": {"input_tokens": 2, "output_tokens": 4, "total_tokens": 6},
        },
    ]

    u = aggregate_usage(msgs)
    assert u.prompt_tokens == 5
    assert u.completion_tokens == 9
    assert u.total_tokens == 14

    turns, steps = count_turns_steps(msgs)
    assert turns == 1
    assert steps == 2

    assert last_stop_reason(msgs) == "end_turn"

    # -------------------------------------------------------------------------
    # Part 2: RunStats dataclass - new enhanced stats tracking
    # -------------------------------------------------------------------------
    # Create a RunStats instance with timestamps
    started = 1000
    ended = 2500
    stats = RunStats(started_ms=started, ended_ms=ended)

    # Test default values
    assert stats.tool_call_count == 0
    assert stats.tool_result_count == 0
    assert stats.tool_error_count == 0
    assert stats.tool_names == {}
    assert stats.tool_latency_total_ms == 0
    assert stats.tool_latency_max_ms == 0
    assert stats.prompt_tokens is None
    assert stats.completion_tokens is None
    assert stats.ttft_ms is None
    assert stats.message_count == 0
    assert stats.turn_count == 0
    assert stats.step_count == 0

    # Test duration_ms property
    assert stats.duration_ms == 1500

    # -------------------------------------------------------------------------
    # Part 3: record_tool_call() and record_tool_result() methods
    # -------------------------------------------------------------------------
    # Record tool calls
    stats.record_tool_call("execute")
    stats.record_tool_call("execute")  # Same tool called twice
    stats.record_tool_call("read_file")

    assert stats.tool_call_count == 3
    assert stats.tool_names == {"execute": 2, "read_file": 1}

    # Record tool results with latency
    stats.record_tool_result("execute", latency_ms=100)
    stats.record_tool_result("execute", latency_ms=200)
    stats.record_tool_result("read_file", latency_ms=50, is_error=True)

    assert stats.tool_result_count == 3
    assert stats.tool_error_count == 1
    assert stats.tool_latency_total_ms == 350
    assert stats.tool_latency_max_ms == 200

    # -------------------------------------------------------------------------
    # Part 4: add_token_usage() method
    # -------------------------------------------------------------------------
    # Add token usage incrementally (simulating multiple API calls)
    stats.add_token_usage(prompt=100, completion=50, total=150)
    stats.add_token_usage(prompt=80, completion=40, total=120, cached=20)
    stats.add_token_usage(reasoning=15)

    assert stats.prompt_tokens == 180
    assert stats.completion_tokens == 90
    assert stats.total_tokens == 270
    assert stats.cached_input_tokens == 20
    assert stats.reasoning_tokens == 15

    # -------------------------------------------------------------------------
    # Part 5: to_dict() for JSON serialization
    # -------------------------------------------------------------------------
    # Set additional fields before serialization
    stats.ttft_ms = 50
    stats.message_count = 5
    stats.turn_count = 2
    stats.step_count = 3
    stats.chunk_count = 10

    d = stats.to_dict()

    # Verify structure
    assert d["duration_ms"] == 1500
    assert d["started_ms"] == 1000
    assert d["ended_ms"] == 2500
    assert d["ttft_ms"] == 50
    assert d["chunk_count"] == 10
    assert d["interrupted"] is False
    assert d["message_count"] == 5
    assert d["turn_count"] == 2
    assert d["step_count"] == 3

    # Tool metrics
    assert d["tool_call_count"] == 3
    assert d["tool_result_count"] == 3
    assert d["tool_error_count"] == 1
    assert d["tool_count"] == 2  # Unique tools: execute, read_file
    assert d["tool_names"] == {"execute": 2, "read_file": 1}
    assert d["tool_latency_ms_total"] == 350
    assert d["tool_latency_ms_avg"] == 350 / 3  # Total / result count
    assert d["tool_latency_ms_max"] == 200

    # Token usage (nested)
    assert "token_usage" in d
    assert d["token_usage"]["prompt_tokens"] == 180
    assert d["token_usage"]["completion_tokens"] == 90
    assert d["token_usage"]["total_tokens"] == 270
    assert d["token_usage"]["cached_input_tokens"] == 20
    assert d["token_usage"]["reasoning_tokens"] == 15

    # -------------------------------------------------------------------------
    # Part 6: now_ms() helper function
    # -------------------------------------------------------------------------
    ts = now_ms()
    assert isinstance(ts, int)
    assert ts > 0

    # -------------------------------------------------------------------------
    # Part 7: RunStatsCollector context manager
    # -------------------------------------------------------------------------
    # Demonstrate the collector pattern (without actual streaming)
    with RunStatsCollector() as collector:
        # Verify timing started
        assert collector.stats.started_ms > 0

        # Access stats during collection
        assert collector.stats.chunk_count == 0

    # After context exit, timing is finalized
    assert collector.stats.ended_ms > 0
    assert collector.stats.ended_ms >= collector.stats.started_ms

    # Test manual start/finish pattern
    collector2 = RunStatsCollector()
    collector2.start()
    assert collector2.stats.started_ms > 0
    collector2.finish()
    assert collector2.stats.ended_ms >= collector2.stats.started_ms

    # Test interrupt handling
    with RunStatsCollector() as collector3:
        # Simulate observing an interrupt chunk
        events = collector3.observe_chunk({"__interrupt__": True})
        assert collector3.stats.interrupted is True
        assert events == []  # No events returned for interrupt

    # Test helper methods
    collector4 = RunStatsCollector()
    assert collector4.get_tool_call_ids() == set()
    assert collector4.get_tool_result_ids() == set()
    assert collector4.get_tool_call_start_time("tc_1") is None
    assert collector4.last_snapshot is None

    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

