"""Compaction state enumeration."""

from enum import Enum


class CompactionState(Enum):
    """States in the compaction lifecycle.

    State transitions:
    IDLE → TRIGGERED → COMPACTING → REBUILDING → COMPLETE
                    ↓↘
                  FAILED
    """
    IDLE = "idle"              # No compaction active
    TRIGGERED = "triggered"    # Threshold exceeded, preparing
    COMPACTING = "compacting"  # Actively summarizing content
    REBUILDING = "rebuilding"  # Rebuilding conversation history
    COMPLETE = "complete"      # Successfully finished
    FAILED = "failed"          # Error occurred
