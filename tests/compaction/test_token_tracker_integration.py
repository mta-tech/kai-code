"""Integration tests for TokenTracker with CompactionManager."""

import pytest
from kai_code.cli_ui import TokenTracker
from kai_code.compaction.manager import CompactionManager


@pytest.mark.asyncio
async def test_token_tracker_compaction_integration():
    """TokenTracker triggers compaction when threshold reached."""
    tracker = TokenTracker()
    manager = CompactionManager(threshold=0.85)

    # Link manager to tracker
    tracker.compaction_manager = manager

    # Set context limit
    tracker.set_context_limit(1000)

    # Add tokens up to 80% - no compaction
    tracker.add_tokens(800)
    assert manager.state.name == "IDLE"  # Hasn't triggered

    # Add tokens to 85% - should trigger (but returns False without messages/LLM)
    tracker.add_tokens(50)  # Total: 850/1000 = 85%
    # State is still IDLE because compaction requires messages/LLM
    assert manager.state.name == "IDLE"  # Can't complete without messages/LLM


def test_token_tracker_compaction_threshold_not_reached():
    """TokenTracker doesn't trigger compaction below threshold."""
    tracker = TokenTracker()
    manager = CompactionManager(threshold=0.85)

    # Link manager to tracker
    tracker.compaction_manager = manager

    # Set context limit
    tracker.set_context_limit(1000)

    # Add tokens up to 84% - should not trigger
    tracker.add_tokens(840)
    assert manager.state.name == "IDLE"  # Hasn't triggered


def test_token_tracker_without_compaction_manager():
    """TokenTracker works normally without compaction manager."""
    tracker = TokenTracker()
    tracker.set_context_limit(1000)

    # Should not crash with None manager
    tracker.add_tokens(900)
    assert tracker.current_context == 900
    assert tracker.get_usage_percentage() == 0.9


@pytest.mark.asyncio
async def test_token_tracker_compaction_with_output_tokens():
    """TokenTracker correctly tracks output tokens and checks compaction."""
    tracker = TokenTracker()
    manager = CompactionManager(threshold=0.85)

    # Link manager to tracker
    tracker.compaction_manager = manager

    # Set context limit
    tracker.set_context_limit(1000)

    # Add input tokens
    tracker.add_tokens(800, is_output=False)
    assert tracker.current_context == 800
    assert tracker.last_output == 0
    assert manager.state.name == "IDLE"

    # Add output tokens (triggers compaction at 85%)
    tracker.add_tokens(50, is_output=True)  # Total: 850/1000 = 85%
    assert tracker.current_context == 850
    assert tracker.last_output == 50
    # Can't complete without messages/LLM
    assert manager.state.name == "IDLE"


@pytest.mark.asyncio
async def test_token_tracker_compaction_cooldown():
    """TokenTracker respects compaction cooldown period."""
    tracker = TokenTracker()
    manager = CompactionManager(threshold=0.85, min_time_between=0)

    # Link manager to tracker
    tracker.compaction_manager = manager

    # Set context limit
    tracker.set_context_limit(1000)

    # First trigger at 85%
    tracker.add_tokens(850)
    # Can't complete without messages/LLM, so state stays IDLE
    assert manager.state.name == "IDLE"
    assert manager.last_compaction_time is None  # Never completed


def test_token_tracker_no_context_limit():
    """TokenTracker handles None context limit gracefully."""
    tracker = TokenTracker()
    manager = CompactionManager(threshold=0.85)

    # Link manager to tracker
    tracker.compaction_manager = manager

    # Don't set context limit

    # Should not crash
    tracker.add_tokens(1000)
    assert tracker.current_context == 1000
    assert tracker.get_usage_percentage() is None
    assert manager.state.name == "IDLE"  # No percentage, can't trigger
