"""Tests for CompactionState enum."""

import pytest
from kai_code.compaction.state import CompactionState


def test_state_values():
    """CompactionState has all expected values."""
    assert CompactionState.IDLE.value == "idle"
    assert CompactionState.TRIGGERED.value == "triggered"
    assert CompactionState.COMPACTING.value == "compacting"
    assert CompactionState.REBUILDING.value == "rebuilding"
    assert CompactionState.COMPLETE.value == "complete"
    assert CompactionState.FAILED.value == "failed"


def test_state_comparison():
    """States can be compared."""
    state = CompactionState.IDLE
    assert state == CompactionState.IDLE
    assert state != CompactionState.COMPACTING
