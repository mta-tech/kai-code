"""Enhanced status display wrapper for Rich's status spinner.

This module provides an EnhancedStatus class that wraps Rich's console.status()
to support dynamic progress updates from ToolProgress objects, including
phase indicators, progress percentages, and phase-specific spinner styles.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from rich.console import Console
from rich.status import Status

from kai_code.progress import ProgressPhase, ToolProgress
from kai_code.rich_config import COLORS

if TYPE_CHECKING:
    from rich.spinner import Spinner


# Spinner styles for each progress phase
# Maps ProgressPhase to Rich spinner names
PHASE_SPINNERS: dict[ProgressPhase, str] = {
    ProgressPhase.STARTING: "dots",
    ProgressPhase.CONNECTING: "dots2",
    ProgressPhase.PROCESSING: "dots3",
    ProgressPhase.DOWNLOADING: "dots8",
    ProgressPhase.FINALIZING: "dots12",
    ProgressPhase.COMPLETE: "dots",
}

# Human-readable phase labels for display
PHASE_LABELS: dict[ProgressPhase, str] = {
    ProgressPhase.STARTING: "Starting",
    ProgressPhase.CONNECTING: "Connecting",
    ProgressPhase.PROCESSING: "Processing",
    ProgressPhase.DOWNLOADING: "Downloading",
    ProgressPhase.FINALIZING: "Finalizing",
    ProgressPhase.COMPLETE: "Complete",
}

# Default spinner style when no phase is specified
DEFAULT_SPINNER = "dots"


class EnhancedStatus:
    """Enhanced wrapper around Rich's Status for progress-aware display.

    This class provides a drop-in replacement for console.status() that can
    handle ToolProgress updates and display them with dynamic spinner text,
    phase indicators, and optional percentage.

    The display format varies based on available progress information:
    - With percent: "{spinner} {phase}: {message} [{percent}%]"
    - Without percent: "{spinner} {phase}: {message}"
    - Without phase: "{spinner} {message}"

    Different spinner styles are used for different progress phases to provide
    visual feedback about what type of operation is occurring.

    Attributes:
        console: The Rich Console instance to use for display
        default_message: The default status message when no progress is reported

    Example:
        # Basic usage
        status = EnhancedStatus(console, "Agent is thinking...")
        status.start()

        # Update with progress
        progress = ToolProgress(
            tool_name="web_search",
            status_message="Searching...",
            percent_complete=50.0,
            phase=ProgressPhase.PROCESSING
        )
        status.update_from_progress(progress)

        status.stop()
    """

    def __init__(
        self,
        console: Console,
        default_message: str,
        *,
        spinner: str = DEFAULT_SPINNER,
    ) -> None:
        """Initialize the EnhancedStatus wrapper.

        Args:
            console: The Rich Console to use for display
            default_message: Initial status message to display
            spinner: Default spinner style (name from Rich spinners)
        """
        self._console = console
        self._default_message = default_message
        self._default_spinner = spinner
        self._current_spinner = spinner
        self._status: Status | None = None
        self._is_running = False
        self._current_progress: ToolProgress | None = None

    @property
    def is_running(self) -> bool:
        """Check if the status spinner is currently active."""
        return self._is_running

    def _format_status_text(self, progress: ToolProgress) -> str:
        """Format the status text from a ToolProgress object.

        Generates display text based on available progress information:
        - With percent and phase: "{phase}: {message} [{percent:.0f}%]"
        - With phase only: "{phase}: {message}"
        - With percent only: "{message} [{percent:.0f}%]"
        - Message only: "{message}"

        Args:
            progress: The progress information to format

        Returns:
            Formatted status text string with Rich markup
        """
        message = progress.status_message
        phase = progress.phase
        percent = progress.percent_complete

        # Build the status text based on available information
        parts: list[str] = []

        # Add phase label if available
        if phase is not None:
            phase_label = PHASE_LABELS.get(phase, phase.value.capitalize())
            parts.append(f"[bold]{phase_label}[/bold]:")

        # Add the message
        parts.append(message)

        # Add percentage if available
        if percent is not None:
            parts.append(f"[{percent:.0f}%]")

        # Join parts with spaces
        text = " ".join(parts)

        # Apply the thinking color style
        return f"[{COLORS['thinking']}]{text}"

    def _get_spinner_for_phase(self, phase: ProgressPhase | None) -> str:
        """Get the appropriate spinner style for a progress phase.

        Args:
            phase: The progress phase, or None for default

        Returns:
            Rich spinner name appropriate for the phase
        """
        if phase is None:
            return self._default_spinner
        return PHASE_SPINNERS.get(phase, self._default_spinner)

    def start(self) -> None:
        """Start displaying the status spinner.

        Creates and starts the underlying Rich Status object with the
        default message and spinner style.
        """
        if self._is_running:
            return

        # Create the status with the default message
        formatted_message = f"[bold {COLORS['thinking']}]{self._default_message}"
        self._status = self._console.status(
            formatted_message,
            spinner=self._default_spinner,
        )
        self._status.start()
        self._is_running = True
        self._current_spinner = self._default_spinner

    def stop(self) -> None:
        """Stop displaying the status spinner.

        Stops and cleans up the underlying Rich Status object.
        """
        if not self._is_running or self._status is None:
            return

        self._status.stop()
        self._is_running = False
        self._current_progress = None

    def update(self, message: str, *, spinner: str | None = None) -> None:
        """Update the status message directly.

        This method provides backward compatibility with the standard
        console.status().update() interface.

        Args:
            message: The new status message to display
            spinner: Optional new spinner style to use
        """
        if not self._is_running or self._status is None:
            return

        # Update spinner if specified and different
        if spinner is not None and spinner != self._current_spinner:
            self._current_spinner = spinner
            # Rich's Status doesn't support changing spinner after creation,
            # but we store it for reference

        self._status.update(message)
        self._current_progress = None

    def update_from_progress(self, progress: ToolProgress) -> None:
        """Update the status display from a ToolProgress object.

        This method formats the progress information and updates the
        spinner text to show the current operation status with phase
        indicators and percentage if available.

        Args:
            progress: The progress information to display
        """
        if not self._is_running or self._status is None:
            return

        self._current_progress = progress

        # Format the status text
        status_text = self._format_status_text(progress)

        # Get appropriate spinner for the phase
        desired_spinner = self._get_spinner_for_phase(progress.phase)

        # Note: Rich's Status doesn't easily support changing spinners after
        # creation without recreating the status. For now, we just update
        # the text. A future enhancement could recreate the status with
        # the new spinner if needed.
        if desired_spinner != self._current_spinner:
            # Store the desired spinner for future reference
            self._current_spinner = desired_spinner

        self._status.update(status_text)

    def reset_to_default(self) -> None:
        """Reset the status to the default message.

        Useful when a tool operation completes and you want to return
        to the default "thinking" state.
        """
        if not self._is_running or self._status is None:
            return

        formatted_message = f"[bold {COLORS['thinking']}]{self._default_message}"
        self._status.update(formatted_message)
        self._current_spinner = self._default_spinner
        self._current_progress = None

    @property
    def current_progress(self) -> ToolProgress | None:
        """Get the current progress being displayed, if any."""
        return self._current_progress


def create_enhanced_status(
    console: Console,
    message: str = "Agent is thinking...",
    *,
    spinner: str = DEFAULT_SPINNER,
) -> EnhancedStatus:
    """Factory function to create an EnhancedStatus instance.

    This provides a convenient way to create an EnhancedStatus with
    sensible defaults.

    Args:
        console: The Rich Console to use
        message: Default status message
        spinner: Default spinner style

    Returns:
        Configured EnhancedStatus instance
    """
    return EnhancedStatus(console, message, spinner=spinner)
