"""Progress reporting infrastructure for long-running tool operations.

This module provides data structures and utilities for tools to report their
progress during execution, enabling enhanced status display in the CLI.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Callable


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
