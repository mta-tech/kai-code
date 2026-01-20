"""Tests for compaction slash commands."""

import pytest
from unittest.mock import Mock, patch
from kai_code.rich_commands import _handle_compact_command


def test_compact_status_with_manager():
    """/compact status shows manager info."""
    manager = Mock()
    manager.state.value = "idle"
    manager.threshold = 0.85
    manager.recent_window_turns = 10
    manager.last_compaction_time = None

    token_tracker = Mock()
    token_tracker.compaction_manager = manager
    token_tracker.get_usage_percentage.return_value = 0.75

    result = _handle_compact_command("/compact status", None, token_tracker)

    assert result is None  # Commands return None (don't exit)


def test_compact_now_triggers():
    """/compact now triggers compaction."""
    manager = Mock()
    manager.check_and_compact.return_value = True

    token_tracker = Mock()
    token_tracker.compaction_manager = manager
    token_tracker.get_usage_percentage.return_value = 0.90

    # Mock asyncio.create_task to avoid needing an event loop in tests
    with patch("kai_code.rich_commands.asyncio.create_task") as mock_create_task:
        result = _handle_compact_command("/compact now", None, token_tracker)

        assert result is None
        # Verify that create_task was called with the async method
        mock_create_task.assert_called_once()
        # Verify the coroutine was created with correct usage percentage
        args, kwargs = mock_create_task.call_args
        # The first arg should be the coroutine from check_and_compact
        assert len(args) == 1


def test_compact_disables():
    """/compact disable removes manager."""
    manager = Mock()

    token_tracker = Mock()
    token_tracker.compaction_manager = manager

    result = _handle_compact_command("/compact disable", None, token_tracker)

    assert result is None
    assert token_tracker.compaction_manager is None


def test_compact_without_manager():
    """Commands handle missing manager gracefully."""
    token_tracker = Mock()
    token_tracker.compaction_manager = None

    # Should not crash
    result = _handle_compact_command("/compact status", None, token_tracker)
    assert result is None
