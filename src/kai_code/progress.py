"""Progress reporting infrastructure for long-running tool operations.

This module provides data structures and utilities for tools to report their
progress during execution, enabling enhanced status display in the CLI.
"""

from __future__ import annotations

import threading
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Callable, Generator


class ProgressPhase(str, Enum):
    """Phases of progress that a tool operation can be in.

    Tools report their current phase to provide context about what
    stage of the operation is currently executing.
    """

    STARTING = "starting"
    CONNECTING = "connecting"
    PROCESSING = "processing"
    DOWNLOADING = "downloading"
    FINALIZING = "finalizing"
    COMPLETE = "complete"


@dataclass
class ToolProgress:
    """Progress information reported by a tool during execution.

    Attributes:
        tool_name: Name of the tool reporting progress (e.g., "web_search", "read_file")
        status_message: Human-readable message describing current operation
        percent_complete: Optional progress percentage (0.0 to 100.0)
        phase: Optional phase indicator for the current operation stage
        details: Optional additional details as a dictionary
    """

    tool_name: str
    status_message: str
    percent_complete: float | None = None
    phase: ProgressPhase | None = None
    details: dict[str, Any] | None = field(default=None)

    def __post_init__(self) -> None:
        """Validate progress values after initialization."""
        if self.percent_complete is not None:
            if self.percent_complete < 0.0:
                self.percent_complete = 0.0
            elif self.percent_complete > 100.0:
                self.percent_complete = 100.0

    def to_dict(self) -> dict[str, Any]:
        """Convert progress to a dictionary for serialization.

        Returns:
            Dictionary representation of the progress, with phase
            converted to its string value.
        """
        result = asdict(self)
        if result.get("phase") is not None:
            result["phase"] = self.phase.value if self.phase else None
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ToolProgress:
        """Create a ToolProgress instance from a dictionary.

        Args:
            data: Dictionary with progress fields

        Returns:
            ToolProgress instance
        """
        phase_value = data.get("phase")
        phase = None
        if phase_value is not None:
            if isinstance(phase_value, ProgressPhase):
                phase = phase_value
            elif isinstance(phase_value, str):
                try:
                    phase = ProgressPhase(phase_value)
                except ValueError:
                    pass

        return cls(
            tool_name=data.get("tool_name", ""),
            status_message=data.get("status_message", ""),
            percent_complete=data.get("percent_complete"),
            phase=phase,
            details=data.get("details"),
        )

    def with_percent(self, percent: float) -> ToolProgress:
        """Create a new progress with updated percentage.

        Args:
            percent: New percentage value (0.0 to 100.0)

        Returns:
            New ToolProgress instance with updated percentage
        """
        return ToolProgress(
            tool_name=self.tool_name,
            status_message=self.status_message,
            percent_complete=percent,
            phase=self.phase,
            details=self.details,
        )

    def with_message(self, message: str) -> ToolProgress:
        """Create a new progress with updated message.

        Args:
            message: New status message

        Returns:
            New ToolProgress instance with updated message
        """
        return ToolProgress(
            tool_name=self.tool_name,
            status_message=message,
            percent_complete=self.percent_complete,
            phase=self.phase,
            details=self.details,
        )

    def with_phase(self, phase: ProgressPhase) -> ToolProgress:
        """Create a new progress with updated phase.

        Args:
            phase: New progress phase

        Returns:
            New ToolProgress instance with updated phase
        """
        return ToolProgress(
            tool_name=self.tool_name,
            status_message=self.status_message,
            percent_complete=self.percent_complete,
            phase=phase,
            details=self.details,
        )


# Type alias for progress callback function that tools can call
# to report their current progress during execution
ProgressCallback = Callable[[ToolProgress], None]


class ProgressManager:
    """Thread-safe manager for progress reporting during tool execution.

    This singleton class holds the current progress callback and provides
    methods for tools to report their progress. It supports scoped progress
    reporting via context managers, allowing rich_execution.py to receive
    progress updates in real-time.

    Thread Safety:
        All operations are protected by a lock to ensure safe concurrent
        access from multiple tool executions.

    Usage:
        # In rich_execution.py - set up the callback
        manager = get_progress_manager()
        manager.set_callback(lambda p: status.update(p.status_message))

        # In tool implementations - report progress
        manager = get_progress_manager()
        manager.report(ToolProgress(
            tool_name="web_search",
            status_message="Connecting to API...",
            phase=ProgressPhase.CONNECTING
        ))

        # Using context manager for scoped progress
        with manager.progress_scope(callback_fn):
            # Progress reports within this scope use callback_fn
            manager.report(progress)
    """

    def __init__(self) -> None:
        """Initialize the ProgressManager with no callback set."""
        self._lock = threading.Lock()
        self._callback: ProgressCallback | None = None
        self._callback_stack: list[ProgressCallback | None] = []

    def set_callback(self, callback: ProgressCallback | None) -> None:
        """Set the progress callback function.

        Args:
            callback: Function to call when progress is reported, or None
                to disable progress reporting.
        """
        with self._lock:
            self._callback = callback

    def clear_callback(self) -> None:
        """Clear the current progress callback.

        After calling this, progress reports will be silently ignored
        until a new callback is set.
        """
        with self._lock:
            self._callback = None

    def get_callback(self) -> ProgressCallback | None:
        """Get the current progress callback.

        Returns:
            The current callback function, or None if not set.
        """
        with self._lock:
            return self._callback

    def report(self, progress: ToolProgress) -> None:
        """Report progress to the current callback.

        If no callback is set, the progress is silently ignored.
        This method is thread-safe.

        Args:
            progress: The progress information to report.
        """
        with self._lock:
            callback = self._callback
        # Call callback outside the lock to avoid potential deadlocks
        if callback is not None:
            try:
                callback(progress)
            except Exception:
                # Silently ignore callback errors to avoid disrupting tool execution
                pass

    @contextmanager
    def progress_scope(
        self, callback: ProgressCallback | None
    ) -> Generator[None, None, None]:
        """Context manager for scoped progress reporting.

        Temporarily sets the progress callback for the duration of the
        context. When the context exits, the previous callback is restored.
        This allows nested progress scopes with different callbacks.

        Args:
            callback: The callback to use within this scope, or None to
                disable progress reporting in this scope.

        Yields:
            None - the context manager doesn't produce a value.

        Example:
            with manager.progress_scope(my_callback):
                # Progress reports go to my_callback
                manager.report(progress1)

                with manager.progress_scope(other_callback):
                    # Progress reports go to other_callback
                    manager.report(progress2)

                # Back to my_callback
                manager.report(progress3)
        """
        with self._lock:
            self._callback_stack.append(self._callback)
            self._callback = callback
        try:
            yield
        finally:
            with self._lock:
                if self._callback_stack:
                    self._callback = self._callback_stack.pop()
                else:
                    self._callback = None


# Module-level singleton instance
_progress_manager: ProgressManager | None = None
_manager_lock = threading.Lock()


def get_progress_manager() -> ProgressManager:
    """Get the singleton ProgressManager instance.

    This function is thread-safe and will create the manager on first call.

    Returns:
        The singleton ProgressManager instance.

    Example:
        manager = get_progress_manager()
        manager.set_callback(my_progress_handler)
        manager.report(ToolProgress(tool_name="test", status_message="Working..."))
    """
    global _progress_manager
    if _progress_manager is None:
        with _manager_lock:
            # Double-check pattern for thread safety
            if _progress_manager is None:
                _progress_manager = ProgressManager()
    return _progress_manager


def reset_progress_manager() -> None:
    """Reset the singleton ProgressManager instance.

    This is primarily useful for testing to ensure a clean state
    between tests. In production code, the singleton should persist
    for the lifetime of the application.
    """
    global _progress_manager
    with _manager_lock:
        _progress_manager = None


@dataclass
class ProgressBar:
    """Simple progress tracker for multi-step operations.

    This provides a basic progress tracking mechanism for operations
    that can be broken down into discrete steps. It's simpler than
    the ToolProgress/ProgressManager system and is useful for
    tracking high-level operation progress.

    Attributes:
        total: Total number of steps/items to complete
        current: Current number of steps/items completed
        steps: Optional list of named steps with their status

    Example:
        progress = ProgressBar(total=4)
        progress.add_step("Initialize")
        progress.add_step("Configure")
        progress.add_step("Execute")
        progress.add_step("Finalize")

        progress.update(1)  # Complete first step
        print(progress.format())  # "25% (1/4)"

        progress.update(1)  # Complete second step
        print(progress.render())  # Shows progress with step list
    """

    total: int
    current: int = 0
    steps: list[dict[str, str]] = field(default_factory=list)

    def update(self, count: int = 1) -> None:
        """Update progress by count.

        Args:
            count: Number of steps completed (default: 1)

        Example:
            progress = ProgressBar(total=10)
            progress.update(3)  # Complete 3 steps
            assert progress.current == 3
        """
        self.current = min(self.current + count, self.total)

    def add_step(self, name: str, status: str = "pending") -> None:
        """Add a named step to track.

        Args:
            name: Step name
            status: Step status (pending, in_progress, complete)

        Example:
            progress = ProgressBar(total=3)
            progress.add_step("Initialize", "pending")
            progress.add_step("Process", "in_progress")
            progress.add_step("Complete", "pending")
        """
        self.steps.append({"name": name, "status": status})

    def get_steps(self) -> list[dict[str, str]]:
        """Get all tracked steps.

        Returns:
            List of step dictionaries with 'name' and 'status' keys

        Example:
            progress = ProgressBar(total=2)
            progress.add_step("Step 1")
            progress.add_step("Step 2")
            steps = progress.get_steps()
            assert len(steps) == 2
        """
        return self.steps

    def is_complete(self) -> bool:
        """Check if progress is complete.

        Returns:
            True if current >= total, False otherwise

        Example:
            progress = ProgressBar(total=4)
            progress.update(4)
            assert progress.is_complete() is True
        """
        return self.current >= self.total

    def format(self) -> str:
        """Format progress as string.

        Returns:
            Formatted progress string with percentage and fraction

        Example:
            progress = ProgressBar(total=4)
            progress.update(1)
            assert progress.format() == "25% (1/4)"
        """
        if self.total == 0:
            return "0% (0/0)"

        percentage = int((self.current / self.total) * 100)
        return f"{percentage}% ({self.current}/{self.total})"

    def render(self) -> str:
        """Render progress bar as string.

        Returns:
            Multi-line progress bar display with percentage and optional steps

        Example:
            progress = ProgressBar(total=3)
            progress.add_step("Step 1")
            progress.add_step("Step 2")
            print(progress.render())
            # Output:
            # Progress: 0% (0/3)
            #     Step 1: Step 1
            #     Step 2: Step 2
        """
        lines = []
        lines.append(f"Progress: {self.format()}")

        if self.steps:
            for i, step in enumerate(self.steps):
                status_icon = {
                    "complete": "✓",
                    "in_progress": "⏳",
                    "pending": " ",
                }.get(step["status"], " ")

                lines.append(f"  {status_icon} Step {i + 1}: {step['name']}")

        return "\n".join(lines)
