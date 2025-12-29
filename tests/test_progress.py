"""Unit tests for progress reporting infrastructure."""

from __future__ import annotations

from kai_code.progress import ProgressCallback, ProgressPhase, ToolProgress


class TestProgressPhase:
    """Tests for the ProgressPhase enum."""

    def test_phase_values(self) -> None:
        """Test that all expected phases exist with correct values."""
        assert ProgressPhase.STARTING.value == "starting"
        assert ProgressPhase.CONNECTING.value == "connecting"
        assert ProgressPhase.PROCESSING.value == "processing"
        assert ProgressPhase.DOWNLOADING.value == "downloading"
        assert ProgressPhase.FINALIZING.value == "finalizing"
        assert ProgressPhase.COMPLETE.value == "complete"

    def test_phase_is_string_enum(self) -> None:
        """Test that phases can be used as strings."""
        phase = ProgressPhase.CONNECTING
        assert isinstance(phase, str)
        assert phase == "connecting"

    def test_phase_from_string(self) -> None:
        """Test creating a phase from its string value."""
        phase = ProgressPhase("processing")
        assert phase == ProgressPhase.PROCESSING


class TestToolProgress:
    """Tests for the ToolProgress dataclass."""

    def test_basic_creation(self) -> None:
        """Test creating a ToolProgress with required fields only."""
        progress = ToolProgress(
            tool_name="web_search",
            status_message="Searching for results...",
        )
        assert progress.tool_name == "web_search"
        assert progress.status_message == "Searching for results..."
        assert progress.percent_complete is None
        assert progress.phase is None
        assert progress.details is None

    def test_full_creation(self) -> None:
        """Test creating a ToolProgress with all fields."""
        progress = ToolProgress(
            tool_name="http_request",
            status_message="Downloading response...",
            percent_complete=75.5,
            phase=ProgressPhase.DOWNLOADING,
            details={"url": "https://example.com", "size": 1024},
        )
        assert progress.tool_name == "http_request"
        assert progress.status_message == "Downloading response..."
        assert progress.percent_complete == 75.5
        assert progress.phase == ProgressPhase.DOWNLOADING
        assert progress.details == {"url": "https://example.com", "size": 1024}

    def test_percent_clamping_below_zero(self) -> None:
        """Test that negative percent is clamped to 0."""
        progress = ToolProgress(
            tool_name="test",
            status_message="test",
            percent_complete=-10.0,
        )
        assert progress.percent_complete == 0.0

    def test_percent_clamping_above_hundred(self) -> None:
        """Test that percent above 100 is clamped to 100."""
        progress = ToolProgress(
            tool_name="test",
            status_message="test",
            percent_complete=150.0,
        )
        assert progress.percent_complete == 100.0


class TestToolProgressSerialization:
    """Tests for ToolProgress serialization methods."""

    def test_to_dict_basic(self) -> None:
        """Test to_dict with basic fields."""
        progress = ToolProgress(
            tool_name="read_file",
            status_message="Reading file...",
        )
        data = progress.to_dict()
        assert data["tool_name"] == "read_file"
        assert data["status_message"] == "Reading file..."
        assert data["percent_complete"] is None
        assert data["phase"] is None
        assert data["details"] is None

    def test_to_dict_with_phase(self) -> None:
        """Test to_dict converts phase enum to string value."""
        progress = ToolProgress(
            tool_name="web_search",
            status_message="Connecting...",
            phase=ProgressPhase.CONNECTING,
        )
        data = progress.to_dict()
        assert data["phase"] == "connecting"

    def test_to_dict_full(self) -> None:
        """Test to_dict with all fields populated."""
        progress = ToolProgress(
            tool_name="fetch_url",
            status_message="Downloading...",
            percent_complete=50.0,
            phase=ProgressPhase.DOWNLOADING,
            details={"bytes_received": 5000, "total_bytes": 10000},
        )
        data = progress.to_dict()
        assert data == {
            "tool_name": "fetch_url",
            "status_message": "Downloading...",
            "percent_complete": 50.0,
            "phase": "downloading",
            "details": {"bytes_received": 5000, "total_bytes": 10000},
        }

    def test_from_dict_basic(self) -> None:
        """Test from_dict with basic fields."""
        data = {
            "tool_name": "glob",
            "status_message": "Searching files...",
        }
        progress = ToolProgress.from_dict(data)
        assert progress.tool_name == "glob"
        assert progress.status_message == "Searching files..."
        assert progress.percent_complete is None
        assert progress.phase is None
        assert progress.details is None

    def test_from_dict_with_phase_string(self) -> None:
        """Test from_dict converts phase string to enum."""
        data = {
            "tool_name": "web_search",
            "status_message": "Processing...",
            "phase": "processing",
        }
        progress = ToolProgress.from_dict(data)
        assert progress.phase == ProgressPhase.PROCESSING

    def test_from_dict_with_phase_enum(self) -> None:
        """Test from_dict accepts phase enum directly."""
        data = {
            "tool_name": "web_search",
            "status_message": "Starting...",
            "phase": ProgressPhase.STARTING,
        }
        progress = ToolProgress.from_dict(data)
        assert progress.phase == ProgressPhase.STARTING

    def test_from_dict_with_invalid_phase(self) -> None:
        """Test from_dict handles invalid phase gracefully."""
        data = {
            "tool_name": "web_search",
            "status_message": "Working...",
            "phase": "invalid_phase_value",
        }
        progress = ToolProgress.from_dict(data)
        assert progress.phase is None

    def test_from_dict_full(self) -> None:
        """Test from_dict with all fields."""
        data = {
            "tool_name": "http_request",
            "status_message": "Complete",
            "percent_complete": 100.0,
            "phase": "complete",
            "details": {"status_code": 200},
        }
        progress = ToolProgress.from_dict(data)
        assert progress.tool_name == "http_request"
        assert progress.status_message == "Complete"
        assert progress.percent_complete == 100.0
        assert progress.phase == ProgressPhase.COMPLETE
        assert progress.details == {"status_code": 200}

    def test_roundtrip_serialization(self) -> None:
        """Test that to_dict -> from_dict preserves data."""
        original = ToolProgress(
            tool_name="test_tool",
            status_message="Testing roundtrip",
            percent_complete=42.5,
            phase=ProgressPhase.PROCESSING,
            details={"key": "value", "count": 123},
        )
        data = original.to_dict()
        restored = ToolProgress.from_dict(data)

        assert restored.tool_name == original.tool_name
        assert restored.status_message == original.status_message
        assert restored.percent_complete == original.percent_complete
        assert restored.phase == original.phase
        assert restored.details == original.details


class TestToolProgressHelpers:
    """Tests for ToolProgress helper methods."""

    def test_with_percent(self) -> None:
        """Test with_percent creates new instance with updated percent."""
        original = ToolProgress(
            tool_name="download",
            status_message="Downloading...",
            percent_complete=25.0,
            phase=ProgressPhase.DOWNLOADING,
        )
        updated = original.with_percent(75.0)

        # Original unchanged
        assert original.percent_complete == 25.0
        # New instance has updated percent
        assert updated.percent_complete == 75.0
        # Other fields preserved
        assert updated.tool_name == "download"
        assert updated.status_message == "Downloading..."
        assert updated.phase == ProgressPhase.DOWNLOADING

    def test_with_message(self) -> None:
        """Test with_message creates new instance with updated message."""
        original = ToolProgress(
            tool_name="search",
            status_message="Starting search...",
            percent_complete=0.0,
        )
        updated = original.with_message("Search complete!")

        # Original unchanged
        assert original.status_message == "Starting search..."
        # New instance has updated message
        assert updated.status_message == "Search complete!"
        # Other fields preserved
        assert updated.tool_name == "search"
        assert updated.percent_complete == 0.0

    def test_with_phase(self) -> None:
        """Test with_phase creates new instance with updated phase."""
        original = ToolProgress(
            tool_name="request",
            status_message="Making request...",
            phase=ProgressPhase.CONNECTING,
        )
        updated = original.with_phase(ProgressPhase.PROCESSING)

        # Original unchanged
        assert original.phase == ProgressPhase.CONNECTING
        # New instance has updated phase
        assert updated.phase == ProgressPhase.PROCESSING
        # Other fields preserved
        assert updated.tool_name == "request"
        assert updated.status_message == "Making request..."


class TestProgressCallback:
    """Tests for the ProgressCallback type alias."""

    def test_callback_type_accepts_function(self) -> None:
        """Test that ProgressCallback type works with a regular function."""
        received_progress: list[ToolProgress] = []

        def my_callback(progress: ToolProgress) -> None:
            received_progress.append(progress)

        # Type check: this should match ProgressCallback
        callback: ProgressCallback = my_callback

        # Test it works
        progress = ToolProgress(tool_name="test", status_message="Hello")
        callback(progress)

        assert len(received_progress) == 1
        assert received_progress[0].tool_name == "test"
        assert received_progress[0].status_message == "Hello"

    def test_callback_type_accepts_lambda(self) -> None:
        """Test that ProgressCallback type works with a lambda."""
        received: list[ToolProgress] = []

        callback: ProgressCallback = lambda p: received.append(p)

        progress = ToolProgress(
            tool_name="lambda_test",
            status_message="Lambda callback",
        )
        callback(progress)

        assert len(received) == 1
        assert received[0].tool_name == "lambda_test"
