"""Tests for CompactionManager."""

import pytest
import time

from kai_code.compaction.manager import CompactionManager
from kai_code.compaction.state import CompactionState


@pytest.mark.asyncio
async def test_manager_initial_state():
    """Manager starts in IDLE state."""
    manager = CompactionManager()
    assert manager.state == CompactionState.IDLE
    assert manager.last_compaction_time is None


@pytest.mark.asyncio
async def test_manager_triggers_at_threshold():
    """Compaction triggers when usage exceeds threshold."""
    manager = CompactionManager(threshold=0.85)

    # Below threshold - no compaction
    assert not await manager.check_and_compact(0.80)
    assert manager.state == CompactionState.IDLE

    # At threshold - no messages/LLM, so can't compact
    assert not await manager.check_and_compact(0.85)
    assert manager.state == CompactionState.IDLE


@pytest.mark.asyncio
async def test_manager_respects_cooldown():
    """Compaction doesn't run twice within cooldown period."""
    manager = CompactionManager(min_time_between=300)

    # First compaction - no messages/LLM, returns False
    await manager.check_and_compact(0.90)
    first_time = manager.last_compaction_time

    # Immediate second attempt - below threshold and no messages/LLM
    assert not await manager.check_and_compact(0.90)
    # last_compaction_time should be None since compaction never actually completed
    assert manager.last_compaction_time == first_time


@pytest.mark.asyncio
async def test_manager_cooldown_expires():
    """Compaction runs again after cooldown expires."""
    manager = CompactionManager(min_time_between=1)  # 1 second cooldown

    # First compaction - no messages/LLM
    assert not await manager.check_and_compact(0.90)

    # Wait for cooldown
    time.sleep(1.1)

    # Second compaction - still no messages/LLM
    assert not await manager.check_and_compact(0.90)


def test_is_running():
    """is_running() returns True during active states."""
    manager = CompactionManager()

    # IDLE is not running
    assert not manager.is_running()

    # Simulate running state
    manager.state = CompactionState.COMPACTING
    assert manager.is_running()

    manager.state = CompactionState.REBUILDING
    assert manager.is_running()

    # COMPLETE is not running
    manager.state = CompactionState.COMPLETE
    assert not manager.is_running()


@pytest.mark.asyncio
async def test_custom_threshold():
    """Manager can be configured with custom threshold."""
    manager = CompactionManager(threshold=0.90)

    # Below 90% - no trigger
    assert not await manager.check_and_compact(0.85)

    # At 90% - but no messages/LLM
    assert not await manager.check_and_compact(0.90)


def test_custom_recent_window():
    """Manager can be configured with custom recent window."""
    manager = CompactionManager(recent_window_turns=15)
    assert manager.recent_window_turns == 15
    assert manager.selector.recent_window_turns == 15
