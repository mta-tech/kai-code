from __future__ import annotations

import pytest

from kai_code.stats import RunStats, RunStatsCollector, now_ms


class TestRunStatsDefaults:
    """Test RunStats default field values."""

    def test_required_fields(self) -> None:
        """Test that required fields must be provided."""
        stats = RunStats(started_ms=1000, ended_ms=2000)
        assert stats.started_ms == 1000
        assert stats.ended_ms == 2000

    def test_basic_defaults(self) -> None:
        """Test basic counter defaults."""
        stats = RunStats(started_ms=0, ended_ms=0)
        assert stats.chunk_count == 0
        assert stats.interrupted is False

    def test_tool_usage_defaults(self) -> None:
        """Test tool usage metrics have sensible defaults."""
        stats = RunStats(started_ms=0, ended_ms=0)
        assert stats.tool_call_count == 0
        assert stats.tool_result_count == 0
        assert stats.tool_error_count == 0
        assert stats.tool_names == {}
        assert stats.tool_latency_total_ms == 0
        assert stats.tool_latency_max_ms == 0

    def test_token_usage_defaults(self) -> None:
        """Test token usage metrics default to None."""
        stats = RunStats(started_ms=0, ended_ms=0)
        assert stats.prompt_tokens is None
        assert stats.completion_tokens is None
        assert stats.total_tokens is None
        assert stats.cached_input_tokens is None
        assert stats.reasoning_tokens is None

    def test_timing_defaults(self) -> None:
        """Test timing and interaction metrics defaults."""
        stats = RunStats(started_ms=0, ended_ms=0)
        assert stats.ttft_ms is None
        assert stats.message_count == 0
        assert stats.turn_count == 0
        assert stats.step_count == 0

    def test_tool_names_not_shared_between_instances(self) -> None:
        """Test that tool_names dict is not shared between instances."""
        stats1 = RunStats(started_ms=0, ended_ms=0)
        stats2 = RunStats(started_ms=0, ended_ms=0)
        stats1.tool_names["test"] = 1
        assert stats2.tool_names == {}


class TestRunStatsDurationMs:
    """Test the duration_ms property."""

    def test_duration_ms_calculation(self) -> None:
        """Test duration_ms is correctly calculated."""
        stats = RunStats(started_ms=1000, ended_ms=2500)
        assert stats.duration_ms == 1500

    def test_duration_ms_zero_when_same_time(self) -> None:
        """Test duration_ms is zero when start equals end."""
        stats = RunStats(started_ms=1000, ended_ms=1000)
        assert stats.duration_ms == 0

    def test_duration_ms_non_negative(self) -> None:
        """Test duration_ms returns 0 for negative durations."""
        stats = RunStats(started_ms=2000, ended_ms=1000)
        assert stats.duration_ms == 0


class TestRecordToolCall:
    """Test the record_tool_call() method."""

    def test_increments_tool_call_count(self) -> None:
        """Test that tool_call_count is incremented."""
        stats = RunStats(started_ms=0, ended_ms=0)
        stats.record_tool_call("read_file")
        assert stats.tool_call_count == 1
        stats.record_tool_call("write_file")
        assert stats.tool_call_count == 2

    def test_tracks_tool_names(self) -> None:
        """Test that tool names are tracked in tool_names dict."""
        stats = RunStats(started_ms=0, ended_ms=0)
        stats.record_tool_call("read_file")
        stats.record_tool_call("read_file")
        stats.record_tool_call("write_file")
        assert stats.tool_names == {"read_file": 2, "write_file": 1}

    def test_empty_tool_name(self) -> None:
        """Test recording an empty tool name."""
        stats = RunStats(started_ms=0, ended_ms=0)
        stats.record_tool_call("")
        assert stats.tool_call_count == 1
        assert stats.tool_names == {"": 1}


class TestRecordToolResult:
    """Test the record_tool_result() method."""

    def test_increments_tool_result_count(self) -> None:
        """Test that tool_result_count is incremented."""
        stats = RunStats(started_ms=0, ended_ms=0)
        stats.record_tool_result("read_file")
        assert stats.tool_result_count == 1
        stats.record_tool_result("write_file")
        assert stats.tool_result_count == 2

    def test_records_errors(self) -> None:
        """Test that errors are counted."""
        stats = RunStats(started_ms=0, ended_ms=0)
        stats.record_tool_result("read_file", is_error=False)
        stats.record_tool_result("write_file", is_error=True)
        stats.record_tool_result("delete_file", is_error=True)
        assert stats.tool_result_count == 3
        assert stats.tool_error_count == 2

    def test_latency_tracking(self) -> None:
        """Test latency metrics are accumulated correctly."""
        stats = RunStats(started_ms=0, ended_ms=0)
        stats.record_tool_result("read_file", latency_ms=100)
        assert stats.tool_latency_total_ms == 100
        assert stats.tool_latency_max_ms == 100

        stats.record_tool_result("write_file", latency_ms=200)
        assert stats.tool_latency_total_ms == 300
        assert stats.tool_latency_max_ms == 200

        stats.record_tool_result("read_file", latency_ms=50)
        assert stats.tool_latency_total_ms == 350
        assert stats.tool_latency_max_ms == 200  # Max unchanged

    def test_latency_none_ignored(self) -> None:
        """Test that None latency does not affect metrics."""
        stats = RunStats(started_ms=0, ended_ms=0)
        stats.record_tool_result("read_file", latency_ms=100)
        stats.record_tool_result("write_file", latency_ms=None)
        assert stats.tool_latency_total_ms == 100
        assert stats.tool_latency_max_ms == 100

    def test_combined_result_and_error(self) -> None:
        """Test recording a result that is also an error with latency."""
        stats = RunStats(started_ms=0, ended_ms=0)
        stats.record_tool_result("bash", latency_ms=500, is_error=True)
        assert stats.tool_result_count == 1
        assert stats.tool_error_count == 1
        assert stats.tool_latency_total_ms == 500
        assert stats.tool_latency_max_ms == 500


class TestAddTokenUsage:
    """Test the add_token_usage() method."""

    def test_first_usage_initializes(self) -> None:
        """Test that first call initializes from None."""
        stats = RunStats(started_ms=0, ended_ms=0)
        stats.add_token_usage(prompt=100, completion=50, total=150)
        assert stats.prompt_tokens == 100
        assert stats.completion_tokens == 50
        assert stats.total_tokens == 150

    def test_accumulates_values(self) -> None:
        """Test that values are accumulated across calls."""
        stats = RunStats(started_ms=0, ended_ms=0)
        stats.add_token_usage(prompt=100, completion=50, total=150)
        stats.add_token_usage(prompt=200, completion=100, total=300)
        assert stats.prompt_tokens == 300
        assert stats.completion_tokens == 150
        assert stats.total_tokens == 450

    def test_partial_updates(self) -> None:
        """Test that partial updates only affect specified fields."""
        stats = RunStats(started_ms=0, ended_ms=0)
        stats.add_token_usage(prompt=100)
        assert stats.prompt_tokens == 100
        assert stats.completion_tokens is None
        assert stats.total_tokens is None

        stats.add_token_usage(completion=50)
        assert stats.prompt_tokens == 100
        assert stats.completion_tokens == 50
        assert stats.total_tokens is None

    def test_cached_and_reasoning_tokens(self) -> None:
        """Test cached_input_tokens and reasoning_tokens."""
        stats = RunStats(started_ms=0, ended_ms=0)
        stats.add_token_usage(cached=1000, reasoning=500)
        assert stats.cached_input_tokens == 1000
        assert stats.reasoning_tokens == 500

        stats.add_token_usage(cached=500, reasoning=250)
        assert stats.cached_input_tokens == 1500
        assert stats.reasoning_tokens == 750

    def test_none_values_ignored(self) -> None:
        """Test that None values do not reset existing values."""
        stats = RunStats(started_ms=0, ended_ms=0)
        stats.add_token_usage(prompt=100, completion=50)
        stats.add_token_usage(prompt=None, completion=None)
        assert stats.prompt_tokens == 100
        assert stats.completion_tokens == 50


class TestToDict:
    """Test the to_dict() method."""

    def test_basic_structure(self) -> None:
        """Test the basic structure of to_dict output."""
        stats = RunStats(started_ms=1000, ended_ms=2000)
        d = stats.to_dict()

        assert d["started_ms"] == 1000
        assert d["ended_ms"] == 2000
        assert d["duration_ms"] == 1000
        assert d["chunk_count"] == 0
        assert d["interrupted"] is False

    def test_tool_metrics_in_output(self) -> None:
        """Test that tool metrics are included in output."""
        stats = RunStats(started_ms=0, ended_ms=0)
        stats.record_tool_call("read_file")
        stats.record_tool_call("read_file")
        stats.record_tool_call("write_file")
        stats.record_tool_result("read_file", latency_ms=100)
        stats.record_tool_result("read_file", latency_ms=200)
        stats.record_tool_result("write_file", latency_ms=150, is_error=True)

        d = stats.to_dict()

        assert d["tool_call_count"] == 3
        assert d["tool_result_count"] == 3
        assert d["tool_error_count"] == 1
        assert d["tool_count"] == 2
        assert d["tool_names"] == {"read_file": 2, "write_file": 1}
        assert d["tool_latency_ms_total"] == 450
        assert d["tool_latency_ms_avg"] == 150.0
        assert d["tool_latency_ms_max"] == 200

    def test_latency_none_when_no_results(self) -> None:
        """Test that latency metrics are None when no results."""
        stats = RunStats(started_ms=0, ended_ms=0)
        d = stats.to_dict()

        assert d["tool_latency_ms_avg"] is None
        assert d["tool_latency_ms_max"] is None

    def test_token_usage_nested(self) -> None:
        """Test that token usage is nested under token_usage key."""
        stats = RunStats(started_ms=0, ended_ms=0)
        stats.add_token_usage(
            prompt=1000, completion=500, total=1500, cached=100, reasoning=50
        )

        d = stats.to_dict()

        assert "token_usage" in d
        assert d["token_usage"]["prompt_tokens"] == 1000
        assert d["token_usage"]["completion_tokens"] == 500
        assert d["token_usage"]["total_tokens"] == 1500
        assert d["token_usage"]["cached_input_tokens"] == 100
        assert d["token_usage"]["reasoning_tokens"] == 50

    def test_token_usage_all_none(self) -> None:
        """Test token_usage with no values set."""
        stats = RunStats(started_ms=0, ended_ms=0)
        d = stats.to_dict()

        assert d["token_usage"]["prompt_tokens"] is None
        assert d["token_usage"]["completion_tokens"] is None
        assert d["token_usage"]["total_tokens"] is None
        assert d["token_usage"]["cached_input_tokens"] is None
        assert d["token_usage"]["reasoning_tokens"] is None

    def test_timing_metrics_in_output(self) -> None:
        """Test timing and interaction metrics in output."""
        stats = RunStats(started_ms=0, ended_ms=1000)
        stats.ttft_ms = 50
        stats.message_count = 10
        stats.turn_count = 2
        stats.step_count = 5

        d = stats.to_dict()

        assert d["ttft_ms"] == 50
        assert d["message_count"] == 10
        assert d["turn_count"] == 2
        assert d["step_count"] == 5

    def test_tool_names_is_copy(self) -> None:
        """Test that tool_names in output is a copy, not reference."""
        stats = RunStats(started_ms=0, ended_ms=0)
        stats.record_tool_call("read_file")
        d = stats.to_dict()
        d["tool_names"]["write_file"] = 1
        assert "write_file" not in stats.tool_names


class TestNowMs:
    """Test the now_ms() helper function."""

    def test_returns_int(self) -> None:
        """Test that now_ms returns an integer."""
        result = now_ms()
        assert isinstance(result, int)

    def test_returns_reasonable_timestamp(self) -> None:
        """Test that now_ms returns a reasonable millisecond timestamp."""
        result = now_ms()
        # Should be after year 2020 (in milliseconds)
        assert result > 1577836800000
        # Should be before year 2100 (in milliseconds)
        assert result < 4102444800000


class TestRunStatsCollector:
    """Test the RunStatsCollector context manager."""

    def test_context_manager_sets_times(self) -> None:
        """Test that context manager sets started_ms and ended_ms."""
        with RunStatsCollector() as collector:
            pass
        assert collector.stats.started_ms > 0
        assert collector.stats.ended_ms >= collector.stats.started_ms

    def test_manual_start_finish(self) -> None:
        """Test manual start() and finish() without context manager."""
        collector = RunStatsCollector()
        collector.start()
        collector.finish()
        assert collector.stats.started_ms > 0
        assert collector.stats.ended_ms >= collector.stats.started_ms

    def test_stats_property(self) -> None:
        """Test that stats property returns RunStats instance."""
        collector = RunStatsCollector()
        assert isinstance(collector.stats, RunStats)

    def test_last_snapshot_initially_none(self) -> None:
        """Test that last_snapshot is initially None."""
        collector = RunStatsCollector()
        assert collector.last_snapshot is None

    def test_get_tool_call_ids_initially_empty(self) -> None:
        """Test that tool call IDs set is initially empty."""
        collector = RunStatsCollector()
        assert collector.get_tool_call_ids() == set()

    def test_get_tool_result_ids_initially_empty(self) -> None:
        """Test that tool result IDs set is initially empty."""
        collector = RunStatsCollector()
        assert collector.get_tool_result_ids() == set()

    def test_get_tool_call_start_time_returns_none(self) -> None:
        """Test that getting unknown tool call start time returns None."""
        collector = RunStatsCollector()
        assert collector.get_tool_call_start_time("unknown") is None

    def test_observe_chunk_increments_chunk_count(self) -> None:
        """Test that observe_chunk increments chunk_count."""
        with RunStatsCollector() as collector:
            collector.observe_chunk({})
            collector.observe_chunk({})
            collector.observe_chunk({})
        assert collector.stats.chunk_count == 3

    def test_observe_chunk_sets_ttft(self) -> None:
        """Test that first chunk sets ttft_ms."""
        with RunStatsCollector() as collector:
            collector.observe_chunk({})
        assert collector.stats.ttft_ms is not None
        assert collector.stats.ttft_ms >= 0

    def test_observe_chunk_handles_interrupt(self) -> None:
        """Test that interrupt chunk sets interrupted flag."""
        with RunStatsCollector() as collector:
            collector.observe_chunk({"__interrupt__": True})
        assert collector.stats.interrupted is True

    def test_observe_chunk_auto_starts(self) -> None:
        """Test that observe_chunk auto-starts if not started."""
        collector = RunStatsCollector()
        collector.observe_chunk({})
        assert collector.stats.started_ms > 0

    def test_context_manager_exit_returns_false(self) -> None:
        """Test that __exit__ returns False (does not suppress exceptions)."""
        collector = RunStatsCollector()
        result = collector.__exit__(None, None, None)
        assert result is False
