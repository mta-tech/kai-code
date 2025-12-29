"""Unit tests for the EnhancedStatus wrapper class."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from rich.console import Console

from kai_code.progress import ProgressPhase, ToolProgress
from kai_code.rich_status import (
    DEFAULT_SPINNER,
    PHASE_LABELS,
    PHASE_SPINNERS,
    EnhancedStatus,
    create_enhanced_status,
)


class TestPhaseConfiguration:
    """Tests for phase spinner and label configurations."""

    def test_all_phases_have_spinners(self) -> None:
        """Test that all ProgressPhase values have spinner mappings."""
        for phase in ProgressPhase:
            assert phase in PHASE_SPINNERS, f"Missing spinner for {phase}"

    def test_all_phases_have_labels(self) -> None:
        """Test that all ProgressPhase values have label mappings."""
        for phase in ProgressPhase:
            assert phase in PHASE_LABELS, f"Missing label for {phase}"

    def test_spinner_values_are_strings(self) -> None:
        """Test that all spinner values are non-empty strings."""
        for phase, spinner in PHASE_SPINNERS.items():
            assert isinstance(spinner, str), f"Spinner for {phase} is not a string"
            assert len(spinner) > 0, f"Spinner for {phase} is empty"

    def test_label_values_are_strings(self) -> None:
        """Test that all label values are non-empty strings."""
        for phase, label in PHASE_LABELS.items():
            assert isinstance(label, str), f"Label for {phase} is not a string"
            assert len(label) > 0, f"Label for {phase} is empty"


class TestEnhancedStatusCreation:
    """Tests for EnhancedStatus initialization."""

    def test_basic_creation(self) -> None:
        """Test creating EnhancedStatus with required arguments."""
        console = Console(force_terminal=True)
        status = EnhancedStatus(console, "Test message")

        assert status._console is console
        assert status._default_message == "Test message"
        assert status._default_spinner == DEFAULT_SPINNER
        assert not status.is_running
        assert status.current_progress is None

    def test_creation_with_custom_spinner(self) -> None:
        """Test creating EnhancedStatus with custom spinner."""
        console = Console(force_terminal=True)
        status = EnhancedStatus(console, "Test message", spinner="line")

        assert status._default_spinner == "line"

    def test_factory_function(self) -> None:
        """Test create_enhanced_status factory function."""
        console = Console(force_terminal=True)
        status = create_enhanced_status(console)

        assert status._default_message == "Agent is thinking..."
        assert status._default_spinner == DEFAULT_SPINNER

    def test_factory_function_with_custom_args(self) -> None:
        """Test create_enhanced_status with custom arguments."""
        console = Console(force_terminal=True)
        status = create_enhanced_status(
            console,
            message="Custom message",
            spinner="dots2",
        )

        assert status._default_message == "Custom message"
        assert status._default_spinner == "dots2"


class TestEnhancedStatusStartStop:
    """Tests for start/stop lifecycle methods."""

    def test_start_creates_status(self) -> None:
        """Test that start() creates the underlying status."""
        console = Console(force_terminal=True)
        status = EnhancedStatus(console, "Test")

        with patch.object(console, "status") as mock_status:
            mock_status_obj = MagicMock()
            mock_status.return_value = mock_status_obj

            status.start()

            mock_status.assert_called_once()
            mock_status_obj.start.assert_called_once()
            assert status.is_running

    def test_stop_stops_status(self) -> None:
        """Test that stop() stops the underlying status."""
        console = Console(force_terminal=True)
        status = EnhancedStatus(console, "Test")

        with patch.object(console, "status") as mock_status:
            mock_status_obj = MagicMock()
            mock_status.return_value = mock_status_obj

            status.start()
            status.stop()

            mock_status_obj.stop.assert_called_once()
            assert not status.is_running

    def test_start_is_idempotent(self) -> None:
        """Test that calling start() multiple times doesn't create multiple statuses."""
        console = Console(force_terminal=True)
        status = EnhancedStatus(console, "Test")

        with patch.object(console, "status") as mock_status:
            mock_status_obj = MagicMock()
            mock_status.return_value = mock_status_obj

            status.start()
            status.start()
            status.start()

            # Should only create one status
            assert mock_status.call_count == 1
            assert mock_status_obj.start.call_count == 1

    def test_stop_before_start_is_safe(self) -> None:
        """Test that stop() before start() doesn't raise."""
        console = Console(force_terminal=True)
        status = EnhancedStatus(console, "Test")

        # Should not raise
        status.stop()
        assert not status.is_running


class TestEnhancedStatusUpdate:
    """Tests for update methods."""

    def test_update_message(self) -> None:
        """Test basic update() method."""
        console = Console(force_terminal=True)
        status = EnhancedStatus(console, "Default")

        with patch.object(console, "status") as mock_status:
            mock_status_obj = MagicMock()
            mock_status.return_value = mock_status_obj

            status.start()
            status.update("New message")

            mock_status_obj.update.assert_called_once_with("New message")

    def test_update_without_start_is_safe(self) -> None:
        """Test that update() before start() doesn't raise."""
        console = Console(force_terminal=True)
        status = EnhancedStatus(console, "Default")

        # Should not raise
        status.update("New message")

    def test_reset_to_default(self) -> None:
        """Test reset_to_default() restores default message."""
        console = Console(force_terminal=True)
        status = EnhancedStatus(console, "Default message")

        with patch.object(console, "status") as mock_status:
            mock_status_obj = MagicMock()
            mock_status.return_value = mock_status_obj

            status.start()
            status.update("Custom message")
            status.reset_to_default()

            # Last update should contain default message
            last_call = mock_status_obj.update.call_args_list[-1]
            assert "Default message" in last_call[0][0]


class TestEnhancedStatusProgressUpdate:
    """Tests for update_from_progress method."""

    def test_update_with_message_only(self) -> None:
        """Test update with progress that has only a message."""
        console = Console(force_terminal=True)
        status = EnhancedStatus(console, "Default")

        with patch.object(console, "status") as mock_status:
            mock_status_obj = MagicMock()
            mock_status.return_value = mock_status_obj

            status.start()
            progress = ToolProgress(
                tool_name="test_tool",
                status_message="Testing...",
            )
            status.update_from_progress(progress)

            # Check the update was called
            mock_status_obj.update.assert_called()
            call_arg = mock_status_obj.update.call_args[0][0]
            assert "Testing..." in call_arg

    def test_update_with_phase(self) -> None:
        """Test update with progress that has a phase."""
        console = Console(force_terminal=True)
        status = EnhancedStatus(console, "Default")

        with patch.object(console, "status") as mock_status:
            mock_status_obj = MagicMock()
            mock_status.return_value = mock_status_obj

            status.start()
            progress = ToolProgress(
                tool_name="test_tool",
                status_message="Connecting to server...",
                phase=ProgressPhase.CONNECTING,
            )
            status.update_from_progress(progress)

            call_arg = mock_status_obj.update.call_args[0][0]
            assert "Connecting" in call_arg
            assert "Connecting to server..." in call_arg

    def test_update_with_percent(self) -> None:
        """Test update with progress that has a percentage."""
        console = Console(force_terminal=True)
        status = EnhancedStatus(console, "Default")

        with patch.object(console, "status") as mock_status:
            mock_status_obj = MagicMock()
            mock_status.return_value = mock_status_obj

            status.start()
            progress = ToolProgress(
                tool_name="test_tool",
                status_message="Downloading...",
                percent_complete=75.5,
            )
            status.update_from_progress(progress)

            call_arg = mock_status_obj.update.call_args[0][0]
            assert "Downloading..." in call_arg
            assert "[76%]" in call_arg  # Rounded to nearest integer

    def test_update_with_all_fields(self) -> None:
        """Test update with progress that has all fields."""
        console = Console(force_terminal=True)
        status = EnhancedStatus(console, "Default")

        with patch.object(console, "status") as mock_status:
            mock_status_obj = MagicMock()
            mock_status.return_value = mock_status_obj

            status.start()
            progress = ToolProgress(
                tool_name="http_request",
                status_message="Fetching data...",
                percent_complete=50.0,
                phase=ProgressPhase.DOWNLOADING,
            )
            status.update_from_progress(progress)

            call_arg = mock_status_obj.update.call_args[0][0]
            assert "Downloading" in call_arg
            assert "Fetching data..." in call_arg
            assert "[50%]" in call_arg

    def test_update_stores_current_progress(self) -> None:
        """Test that update_from_progress stores the current progress."""
        console = Console(force_terminal=True)
        status = EnhancedStatus(console, "Default")

        with patch.object(console, "status") as mock_status:
            mock_status_obj = MagicMock()
            mock_status.return_value = mock_status_obj

            status.start()
            progress = ToolProgress(
                tool_name="test",
                status_message="Testing",
                phase=ProgressPhase.PROCESSING,
            )
            status.update_from_progress(progress)

            assert status.current_progress is progress

    def test_update_without_start_is_safe(self) -> None:
        """Test that update_from_progress before start doesn't raise."""
        console = Console(force_terminal=True)
        status = EnhancedStatus(console, "Default")

        progress = ToolProgress(tool_name="test", status_message="Testing")

        # Should not raise
        status.update_from_progress(progress)


class TestFormatStatusText:
    """Tests for the _format_status_text method."""

    def test_format_message_only(self) -> None:
        """Test formatting with message only."""
        console = Console(force_terminal=True)
        status = EnhancedStatus(console, "Default")

        progress = ToolProgress(
            tool_name="test",
            status_message="Simple message",
        )
        text = status._format_status_text(progress)

        assert "Simple message" in text
        # Should not contain phase label or percentage
        assert ":" not in text.replace("[", "").replace("]", "").split("%")[0].split("Simple")[0]

    def test_format_with_phase(self) -> None:
        """Test formatting with phase label."""
        console = Console(force_terminal=True)
        status = EnhancedStatus(console, "Default")

        progress = ToolProgress(
            tool_name="test",
            status_message="Working hard",
            phase=ProgressPhase.PROCESSING,
        )
        text = status._format_status_text(progress)

        assert "Processing" in text
        assert "Working hard" in text

    def test_format_with_percentage(self) -> None:
        """Test formatting with percentage."""
        console = Console(force_terminal=True)
        status = EnhancedStatus(console, "Default")

        progress = ToolProgress(
            tool_name="test",
            status_message="Almost done",
            percent_complete=99.9,
        )
        text = status._format_status_text(progress)

        assert "Almost done" in text
        assert "[100%]" in text  # Rounded

    def test_format_with_zero_percent(self) -> None:
        """Test formatting with 0 percent."""
        console = Console(force_terminal=True)
        status = EnhancedStatus(console, "Default")

        progress = ToolProgress(
            tool_name="test",
            status_message="Starting",
            percent_complete=0.0,
        )
        text = status._format_status_text(progress)

        assert "[0%]" in text

    def test_format_full(self) -> None:
        """Test formatting with all fields."""
        console = Console(force_terminal=True)
        status = EnhancedStatus(console, "Default")

        progress = ToolProgress(
            tool_name="web_search",
            status_message="Searching for results",
            percent_complete=42.5,
            phase=ProgressPhase.CONNECTING,
        )
        text = status._format_status_text(progress)

        # Verify order: phase, message, percent
        assert "Connecting" in text
        assert "Searching for results" in text
        assert "[43%]" in text  # Rounded


class TestGetSpinnerForPhase:
    """Tests for spinner selection based on phase."""

    def test_get_spinner_for_all_phases(self) -> None:
        """Test that all phases return a valid spinner."""
        console = Console(force_terminal=True)
        status = EnhancedStatus(console, "Default")

        for phase in ProgressPhase:
            spinner = status._get_spinner_for_phase(phase)
            assert isinstance(spinner, str)
            assert len(spinner) > 0

    def test_get_spinner_for_none_returns_default(self) -> None:
        """Test that None phase returns default spinner."""
        console = Console(force_terminal=True)
        status = EnhancedStatus(console, "Default", spinner="custom")

        spinner = status._get_spinner_for_phase(None)
        assert spinner == "custom"

    def test_spinner_varies_by_phase(self) -> None:
        """Test that different phases can have different spinners."""
        console = Console(force_terminal=True)
        status = EnhancedStatus(console, "Default")

        # At least some phases should have different spinners
        spinners = {status._get_spinner_for_phase(phase) for phase in ProgressPhase}
        # We expect at least 2 different spinners across all phases
        assert len(spinners) >= 2


class TestEnhancedStatusIntegration:
    """Integration tests for EnhancedStatus."""

    def test_full_lifecycle(self) -> None:
        """Test a full lifecycle: start, update, stop."""
        console = Console(force_terminal=True)
        status = EnhancedStatus(console, "Thinking...")

        with patch.object(console, "status") as mock_status:
            mock_status_obj = MagicMock()
            mock_status.return_value = mock_status_obj

            # Start
            status.start()
            assert status.is_running

            # Update with progress
            progress1 = ToolProgress(
                tool_name="web_search",
                status_message="Searching...",
                phase=ProgressPhase.CONNECTING,
            )
            status.update_from_progress(progress1)
            assert status.current_progress is progress1

            # Update with more progress
            progress2 = ToolProgress(
                tool_name="web_search",
                status_message="Processing results...",
                percent_complete=75.0,
                phase=ProgressPhase.PROCESSING,
            )
            status.update_from_progress(progress2)
            assert status.current_progress is progress2

            # Reset to default
            status.reset_to_default()
            assert status.current_progress is None

            # Stop
            status.stop()
            assert not status.is_running

    def test_multiple_start_stop_cycles(self) -> None:
        """Test multiple start/stop cycles work correctly."""
        console = Console(force_terminal=True)
        status = EnhancedStatus(console, "Thinking...")

        with patch.object(console, "status") as mock_status:
            mock_status_obj = MagicMock()
            mock_status.return_value = mock_status_obj

            for _ in range(3):
                status.start()
                assert status.is_running

                progress = ToolProgress(
                    tool_name="test",
                    status_message="Working...",
                )
                status.update_from_progress(progress)

                status.stop()
                assert not status.is_running
