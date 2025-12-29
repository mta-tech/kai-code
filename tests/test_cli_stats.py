"""Integration tests for CLI stats output in stream-json format.

Tests that stream-json result events include all new metrics from RunStats.to_dict()
in the expected format as documented in docs/stream-json-schema.md.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# Add src to path to allow direct module imports without triggering __init__.py
_src_path = str(Path(__file__).parent.parent / "src")
if _src_path not in sys.path:
    sys.path.insert(0, _src_path)

# Import stats module directly using importlib to avoid triggering kai_code/__init__.py
import importlib.util

_stats_path = Path(__file__).parent.parent / "src" / "kai_code" / "stats.py"
_stats_spec = importlib.util.spec_from_file_location("kai_code.stats", _stats_path)
_stats_module = importlib.util.module_from_spec(_stats_spec)
# Register in sys.modules before exec to satisfy dataclass inspection
sys.modules["kai_code.stats"] = _stats_module
_stats_spec.loader.exec_module(_stats_module)
RunStats = _stats_module.RunStats


# Try to import CLI main - if it fails due to missing deps, skip CLI tests
try:
    from kai_code.cli import main as cli_main

    _CLI_AVAILABLE = True
except ImportError:
    _CLI_AVAILABLE = False
    cli_main = None

# Marker for tests requiring full CLI
requires_cli = pytest.mark.skipif(
    not _CLI_AVAILABLE,
    reason="Full kai_code package with dependencies required",
)


@requires_cli
class TestDryRunStatsSchema:
    """Test that --dry-run stats output includes all expected fields."""

    def test_stream_json_dry_run_stats_schema(self, capsys) -> None:
        """Test that stream-json dry-run includes complete stats schema."""
        rc = cli_main(["--dry-run", "--output-format", "stream-json", "-p", "test"])
        assert rc == 0

        out = capsys.readouterr().out
        lines = [l for l in out.strip().split("\n") if l]
        assert len(lines) == 2  # init and result events

        # Parse the result event (second line)
        result_event = json.loads(lines[1])
        assert result_event["type"] == "result"
        assert "stats" in result_event

        stats = result_event["stats"]

        # Verify all expected top-level stats fields
        assert "duration_ms" in stats
        assert "ttft_ms" in stats
        assert "chunk_count" in stats

        # Verify tool usage metrics fields
        assert "tool_call_count" in stats
        assert "tool_result_count" in stats

        # Verify token_usage nested structure
        assert "token_usage" in stats
        token_usage = stats["token_usage"]
        assert "prompt_tokens" in token_usage
        assert "completion_tokens" in token_usage
        assert "total_tokens" in token_usage
        assert "cached_input_tokens" in token_usage
        assert "reasoning_tokens" in token_usage

    def test_stream_json_dry_run_stats_values_are_valid(self, capsys) -> None:
        """Test that dry-run stats values are valid (zeros/nulls for dry run)."""
        rc = cli_main(["--dry-run", "--output-format", "stream-json", "-p", "test"])
        assert rc == 0

        out = capsys.readouterr().out
        lines = [l for l in out.strip().split("\n") if l]
        result_event = json.loads(lines[1])
        stats = result_event["stats"]

        # Dry run should have zero/null values
        assert stats["duration_ms"] == 0
        assert stats["ttft_ms"] is None
        assert stats["chunk_count"] == 0
        assert stats["tool_call_count"] == 0
        assert stats["tool_result_count"] == 0

        # Token usage should all be None in dry run
        token_usage = stats["token_usage"]
        assert token_usage["prompt_tokens"] is None
        assert token_usage["completion_tokens"] is None
        assert token_usage["total_tokens"] is None
        assert token_usage["cached_input_tokens"] is None
        assert token_usage["reasoning_tokens"] is None

    def test_dry_run_init_event_schema(self, capsys) -> None:
        """Test that init event includes model/provider info."""
        rc = cli_main(["--dry-run", "--output-format", "stream-json", "-p", "test"])
        assert rc == 0

        out = capsys.readouterr().out
        lines = [l for l in out.strip().split("\n") if l]
        init_event = json.loads(lines[0])

        assert init_event["type"] == "init"
        assert "schema_version" in init_event
        assert init_event["schema_version"] == 1
        assert "run_id" in init_event
        assert "ts_ms" in init_event
        assert "dry_run" in init_event
        assert init_event["dry_run"] is True


class TestRunStatsToDictSchema:
    """Test that RunStats.to_dict() produces the expected schema."""

    def test_to_dict_includes_all_documented_fields(self) -> None:
        """Verify to_dict() includes all fields documented in stream-json-schema.md."""
        stats = RunStats(started_ms=1000, ended_ms=2000)
        d = stats.to_dict()

        # Core timing fields
        assert "duration_ms" in d
        assert "started_ms" in d
        assert "ended_ms" in d
        assert "ttft_ms" in d
        assert "chunk_count" in d
        assert "interrupted" in d

        # Interaction metrics
        assert "message_count" in d
        assert "turn_count" in d
        assert "step_count" in d

        # Tool usage metrics
        assert "tool_call_count" in d
        assert "tool_result_count" in d
        assert "tool_error_count" in d
        assert "tool_count" in d
        assert "tool_names" in d
        assert "tool_latency_ms_total" in d
        assert "tool_latency_ms_avg" in d
        assert "tool_latency_ms_max" in d

        # Token usage (nested)
        assert "token_usage" in d
        token_usage = d["token_usage"]
        assert "prompt_tokens" in token_usage
        assert "completion_tokens" in token_usage
        assert "total_tokens" in token_usage
        assert "cached_input_tokens" in token_usage
        assert "reasoning_tokens" in token_usage

    def test_to_dict_with_tool_metrics_populated(self) -> None:
        """Test to_dict() output with tool metrics populated."""
        stats = RunStats(started_ms=0, ended_ms=1000)
        stats.record_tool_call("Read")
        stats.record_tool_call("Read")
        stats.record_tool_call("Edit")
        stats.record_tool_result("Read", latency_ms=100)
        stats.record_tool_result("Read", latency_ms=200)
        stats.record_tool_result("Edit", latency_ms=150, is_error=True)

        d = stats.to_dict()

        assert d["tool_call_count"] == 3
        assert d["tool_result_count"] == 3
        assert d["tool_error_count"] == 1
        assert d["tool_count"] == 2  # unique tool names
        assert d["tool_names"] == {"Read": 2, "Edit": 1}
        assert d["tool_latency_ms_total"] == 450
        assert d["tool_latency_ms_avg"] == 150.0  # 450 / 3
        assert d["tool_latency_ms_max"] == 200

    def test_to_dict_with_token_usage_populated(self) -> None:
        """Test to_dict() output with token usage populated."""
        stats = RunStats(started_ms=0, ended_ms=1000)
        stats.add_token_usage(
            prompt=1000,
            completion=500,
            total=1500,
            cached=100,
            reasoning=50,
        )

        d = stats.to_dict()
        token_usage = d["token_usage"]

        assert token_usage["prompt_tokens"] == 1000
        assert token_usage["completion_tokens"] == 500
        assert token_usage["total_tokens"] == 1500
        assert token_usage["cached_input_tokens"] == 100
        assert token_usage["reasoning_tokens"] == 50

    def test_to_dict_with_timing_metrics_populated(self) -> None:
        """Test to_dict() output with timing metrics populated."""
        stats = RunStats(started_ms=1000, ended_ms=3000)
        stats.ttft_ms = 50
        stats.chunk_count = 10
        stats.message_count = 5
        stats.turn_count = 2
        stats.step_count = 3
        stats.interrupted = False

        d = stats.to_dict()

        assert d["duration_ms"] == 2000
        assert d["started_ms"] == 1000
        assert d["ended_ms"] == 3000
        assert d["ttft_ms"] == 50
        assert d["chunk_count"] == 10
        assert d["message_count"] == 5
        assert d["turn_count"] == 2
        assert d["step_count"] == 3
        assert d["interrupted"] is False

    def test_to_dict_latency_none_when_no_results(self) -> None:
        """Test that latency avg/max are None when no tool results."""
        stats = RunStats(started_ms=0, ended_ms=0)
        d = stats.to_dict()

        assert d["tool_latency_ms_avg"] is None
        assert d["tool_latency_ms_max"] is None
        assert d["tool_latency_ms_total"] == 0

    def test_to_dict_tool_names_empty_dict_when_no_tools(self) -> None:
        """Test that tool_names is empty dict when no tools used."""
        stats = RunStats(started_ms=0, ended_ms=0)
        d = stats.to_dict()

        assert d["tool_names"] == {}
        assert d["tool_count"] == 0


class TestStatsJsonSerializable:
    """Test that stats output is fully JSON serializable."""

    def test_to_dict_is_json_serializable(self) -> None:
        """Test that RunStats.to_dict() output can be serialized to JSON."""
        stats = RunStats(started_ms=1000, ended_ms=2000)
        stats.record_tool_call("Read")
        stats.record_tool_result("Read", latency_ms=100)
        stats.add_token_usage(prompt=1000, completion=500, total=1500)
        stats.ttft_ms = 50
        stats.chunk_count = 10
        stats.message_count = 5
        stats.turn_count = 2
        stats.step_count = 3

        d = stats.to_dict()

        # Should not raise
        json_str = json.dumps(d)
        assert isinstance(json_str, str)

        # Should round-trip correctly
        parsed = json.loads(json_str)
        assert parsed == d

    def test_to_dict_with_all_none_values_is_json_serializable(self) -> None:
        """Test that stats with None values serializes correctly."""
        stats = RunStats(started_ms=0, ended_ms=0)
        d = stats.to_dict()

        # Should not raise
        json_str = json.dumps(d)
        assert isinstance(json_str, str)

        # Should round-trip correctly
        parsed = json.loads(json_str)
        assert parsed == d

    def test_complete_stats_matches_cli_schema(self) -> None:
        """Test that a complete stats dict matches the expected CLI output format."""
        stats = RunStats(started_ms=1000, ended_ms=3000)
        stats.ttft_ms = 50
        stats.chunk_count = 100
        stats.interrupted = False
        stats.message_count = 10
        stats.turn_count = 2
        stats.step_count = 5

        # Tool usage
        stats.record_tool_call("Read")
        stats.record_tool_call("Read")
        stats.record_tool_call("Edit")
        stats.record_tool_result("Read", latency_ms=100)
        stats.record_tool_result("Read", latency_ms=200)
        stats.record_tool_result("Edit", latency_ms=150)

        # Token usage
        stats.add_token_usage(
            prompt=5000,
            completion=2000,
            total=7000,
            cached=1000,
            reasoning=500,
        )

        d = stats.to_dict()

        # Verify the complete structure
        expected_keys = {
            "duration_ms",
            "started_ms",
            "ended_ms",
            "ttft_ms",
            "chunk_count",
            "interrupted",
            "message_count",
            "turn_count",
            "step_count",
            "tool_call_count",
            "tool_result_count",
            "tool_error_count",
            "tool_count",
            "tool_names",
            "tool_latency_ms_total",
            "tool_latency_ms_avg",
            "tool_latency_ms_max",
            "token_usage",
        }
        assert set(d.keys()) == expected_keys

        # Verify token_usage structure
        expected_token_keys = {
            "prompt_tokens",
            "completion_tokens",
            "total_tokens",
            "cached_input_tokens",
            "reasoning_tokens",
        }
        assert set(d["token_usage"].keys()) == expected_token_keys


@requires_cli
class TestDryRunResultEventSchema:
    """Test the complete result event schema in dry-run mode."""

    def test_result_event_has_all_expected_fields(self, capsys) -> None:
        """Test that result event includes all documented fields."""
        rc = cli_main(["--dry-run", "--output-format", "stream-json", "-p", "test"])
        assert rc == 0

        out = capsys.readouterr().out
        lines = [l for l in out.strip().split("\n") if l]
        result_event = json.loads(lines[1])

        # Required fields per stream-json-schema.md
        assert result_event["type"] == "result"
        assert "schema_version" in result_event
        assert "run_id" in result_event
        assert "event_id" in result_event
        assert "ts_ms" in result_event
        assert "dry_run" in result_event
        assert "output" in result_event
        assert "stop_reason" in result_event
        assert "stats" in result_event

        # stop_reason should be 'dry_run' for dry runs
        assert result_event["stop_reason"] == "dry_run"

    def test_result_stats_matches_schema(self, capsys) -> None:
        """Test that result stats match the documented schema structure."""
        rc = cli_main(["--dry-run", "--output-format", "stream-json", "-p", "test"])
        assert rc == 0

        out = capsys.readouterr().out
        lines = [l for l in out.strip().split("\n") if l]
        result_event = json.loads(lines[1])
        stats = result_event["stats"]

        # Per stream-json-schema.md, stats should include:
        # - duration_ms
        # - ttft_ms
        # - chunk_count
        # - message_count
        # - turn_count
        # - step_count
        # - tool_call_count
        # - tool_result_count
        # - token_usage (nested)
        assert isinstance(stats["duration_ms"], int)
        assert stats["chunk_count"] == 0
        assert "message_count" in stats
        assert "turn_count" in stats
        assert "step_count" in stats
        assert "tool_call_count" in stats
        assert "tool_result_count" in stats
        assert "token_usage" in stats
        assert isinstance(stats["token_usage"], dict)
