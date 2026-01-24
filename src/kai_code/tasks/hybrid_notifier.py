"""Auto-nudge integration for HybridTaskManager.

Provides adapter to bridge new HybridTaskManager.Task type with the
legacy TaskCompletionNotifier system.

The new Task type (from hybrid_manager.py) has a different structure
than the old Task type (from task.py). This adapter provides the
interface that TaskCompletionNotifier expects.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .hybrid_manager import Task as HybridTask


class HybridTaskAdapter:
    """Adapter to make HybridTask compatible with TaskCompletionNotifier.

    The old Task type has fields like `description` while the new HybridTask
    uses `command`. This adapter bridges the gap without modifying either
    the old notifier or the new task manager.
    """

    def __init__(self, task: "HybridTask") -> None:
        """Initialize adapter with a HybridTask."""
        self._task = task

    @property
    def id(self) -> str:
        """Task ID."""
        return self._task.id

    @property
    def description(self) -> str:
        """Task description (mapped from command)."""
        return self._task.command

    @property
    def type(self) -> str:
        """Task type ('shell' or 'agent')."""
        return self._task.type

    @property
    def status(self) -> object:
        """Task status (wraps new TaskStatus)."""
        # Return a wrapper that behaves like old TaskStatus enum
        return _TaskStatusAdapter(self._task.status)

    @property
    def duration(self) -> float | None:
        """Task duration in seconds."""
        return self._task.duration

    @property
    def output(self) -> str:
        """Task output."""
        return self._task.output

    @property
    def error(self) -> str | None:
        """Task error message."""
        return self._task.error


class _TaskStatusAdapter:
    """Adapter for new TaskStatus to behave like old TaskStatus enum.

    Old TaskStatus has `.value` property that returns the status string.
    New TaskStatus IS the enum, but we need to provide the same interface.
    """

    def __init__(self, status: object) -> None:
        """Initialize with a TaskStatus enum value."""
        self._status = status

    @property
    def value(self) -> str:
        """Get status string value."""
        # The new TaskStatus enum values ARE the strings
        return self._status.value


@dataclass
class HybridTaskCompletionNotifier:
    """Auto-nudge callback for HybridTaskManager.

    Wraps the legacy TaskCompletionNotifier to work with HybridTaskManager
    by adapting the task type before passing to the notifier.
    """

    def __init__(self, legacy_notifier: object) -> None:
        """Initialize with legacy TaskCompletionNotifier.

        Args:
            legacy_notifier: Instance of TaskCompletionNotifier from notifier.py
        """
        self._legacy_notifier = legacy_notifier

    def __call__(self, task: "HybridTask") -> None:
        """Called by HybridTaskManager when task completes.

        Adapts the new Task type before passing to legacy notifier.
        """
        # Wrap the new task with adapter
        adapted_task = HybridTaskAdapter(task)
        # Delegate to legacy notifier
        self._legacy_notifier(adapted_task)
