"""Unit tests for progress reporting infrastructure."""

from __future__ import annotations

import threading
import time
from concurrent.futures import ThreadPoolExecutor

import pytest

from kai_code.progress import (
    ProgressCallback,
    ProgressManager,
    ProgressPhase,
    ToolProgress,
    get_progress_manager,
    reset_progress_manager,
)


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


class TestProgressManager:
    """Tests for the ProgressManager class."""

    def setup_method(self) -> None:
        """Reset the singleton before each test."""
        reset_progress_manager()

    def teardown_method(self) -> None:
        """Clean up after each test."""
        reset_progress_manager()

    def test_initial_state(self) -> None:
        """Test that manager starts with no callback."""
        manager = ProgressManager()
        assert manager.get_callback() is None

    def test_set_callback(self) -> None:
        """Test setting a callback."""
        manager = ProgressManager()
        received: list[ToolProgress] = []

        def callback(p: ToolProgress) -> None:
            received.append(p)

        manager.set_callback(callback)
        assert manager.get_callback() is callback

    def test_clear_callback(self) -> None:
        """Test clearing the callback."""
        manager = ProgressManager()

        def callback(p: ToolProgress) -> None:
            pass

        manager.set_callback(callback)
        assert manager.get_callback() is not None

        manager.clear_callback()
        assert manager.get_callback() is None

    def test_report_with_callback(self) -> None:
        """Test reporting progress when callback is set."""
        manager = ProgressManager()
        received: list[ToolProgress] = []

        manager.set_callback(lambda p: received.append(p))

        progress = ToolProgress(
            tool_name="test_tool",
            status_message="Testing...",
            phase=ProgressPhase.PROCESSING,
        )
        manager.report(progress)

        assert len(received) == 1
        assert received[0].tool_name == "test_tool"
        assert received[0].status_message == "Testing..."
        assert received[0].phase == ProgressPhase.PROCESSING

    def test_report_without_callback(self) -> None:
        """Test that report does nothing when no callback is set."""
        manager = ProgressManager()

        # This should not raise any exception
        progress = ToolProgress(tool_name="test", status_message="No callback")
        manager.report(progress)

    def test_report_handles_callback_exception(self) -> None:
        """Test that report silently ignores callback exceptions."""
        manager = ProgressManager()

        def bad_callback(p: ToolProgress) -> None:
            raise ValueError("Callback error!")

        manager.set_callback(bad_callback)

        # Should not raise, even though callback raises
        progress = ToolProgress(tool_name="test", status_message="Error test")
        manager.report(progress)  # No exception should be raised

    def test_multiple_reports(self) -> None:
        """Test multiple progress reports."""
        manager = ProgressManager()
        received: list[ToolProgress] = []

        manager.set_callback(lambda p: received.append(p))

        for i in range(5):
            progress = ToolProgress(
                tool_name="multi_test",
                status_message=f"Step {i}",
                percent_complete=i * 20.0,
            )
            manager.report(progress)

        assert len(received) == 5
        assert received[0].status_message == "Step 0"
        assert received[4].status_message == "Step 4"
        assert received[4].percent_complete == 80.0


class TestProgressManagerContextManager:
    """Tests for ProgressManager context manager support."""

    def setup_method(self) -> None:
        """Reset the singleton before each test."""
        reset_progress_manager()

    def teardown_method(self) -> None:
        """Clean up after each test."""
        reset_progress_manager()

    def test_progress_scope_basic(self) -> None:
        """Test basic progress_scope context manager."""
        manager = ProgressManager()
        received: list[ToolProgress] = []

        with manager.progress_scope(lambda p: received.append(p)):
            manager.report(ToolProgress(tool_name="scoped", status_message="Inside"))

        assert len(received) == 1
        assert received[0].tool_name == "scoped"

    def test_progress_scope_restores_previous(self) -> None:
        """Test that progress_scope restores previous callback."""
        manager = ProgressManager()
        outer_received: list[ToolProgress] = []
        inner_received: list[ToolProgress] = []

        manager.set_callback(lambda p: outer_received.append(p))

        # Report before scope
        manager.report(ToolProgress(tool_name="before", status_message="Before scope"))

        with manager.progress_scope(lambda p: inner_received.append(p)):
            manager.report(ToolProgress(tool_name="inside", status_message="Inside scope"))

        # Report after scope
        manager.report(ToolProgress(tool_name="after", status_message="After scope"))

        # Outer callback should receive before and after
        assert len(outer_received) == 2
        assert outer_received[0].tool_name == "before"
        assert outer_received[1].tool_name == "after"

        # Inner callback should receive only inside
        assert len(inner_received) == 1
        assert inner_received[0].tool_name == "inside"

    def test_progress_scope_nested(self) -> None:
        """Test nested progress_scope contexts."""
        manager = ProgressManager()
        outer_received: list[ToolProgress] = []
        middle_received: list[ToolProgress] = []
        inner_received: list[ToolProgress] = []

        with manager.progress_scope(lambda p: outer_received.append(p)):
            manager.report(ToolProgress(tool_name="outer", status_message="Outer"))

            with manager.progress_scope(lambda p: middle_received.append(p)):
                manager.report(ToolProgress(tool_name="middle", status_message="Middle"))

                with manager.progress_scope(lambda p: inner_received.append(p)):
                    manager.report(ToolProgress(tool_name="inner", status_message="Inner"))

                manager.report(ToolProgress(tool_name="back_middle", status_message="Back to middle"))

            manager.report(ToolProgress(tool_name="back_outer", status_message="Back to outer"))

        assert [p.tool_name for p in outer_received] == ["outer", "back_outer"]
        assert [p.tool_name for p in middle_received] == ["middle", "back_middle"]
        assert [p.tool_name for p in inner_received] == ["inner"]

    def test_progress_scope_with_none(self) -> None:
        """Test progress_scope with None disables reporting."""
        manager = ProgressManager()
        received: list[ToolProgress] = []

        manager.set_callback(lambda p: received.append(p))
        manager.report(ToolProgress(tool_name="before", status_message="Before"))

        with manager.progress_scope(None):
            # This should not be received
            manager.report(ToolProgress(tool_name="suppressed", status_message="Suppressed"))

        manager.report(ToolProgress(tool_name="after", status_message="After"))

        assert len(received) == 2
        assert received[0].tool_name == "before"
        assert received[1].tool_name == "after"

    def test_progress_scope_handles_exception(self) -> None:
        """Test that progress_scope restores callback even when exception occurs."""
        manager = ProgressManager()
        outer_received: list[ToolProgress] = []
        inner_received: list[ToolProgress] = []

        manager.set_callback(lambda p: outer_received.append(p))

        try:
            with manager.progress_scope(lambda p: inner_received.append(p)):
                manager.report(ToolProgress(tool_name="before_error", status_message="Before"))
                raise RuntimeError("Test exception")
        except RuntimeError:
            pass

        # Should be back to outer callback
        manager.report(ToolProgress(tool_name="after_error", status_message="After"))

        assert len(inner_received) == 1
        assert inner_received[0].tool_name == "before_error"
        assert len(outer_received) == 1
        assert outer_received[0].tool_name == "after_error"


class TestProgressManagerThreadSafety:
    """Tests for ProgressManager thread safety."""

    def setup_method(self) -> None:
        """Reset the singleton before each test."""
        reset_progress_manager()

    def teardown_method(self) -> None:
        """Clean up after each test."""
        reset_progress_manager()

    def test_concurrent_reports(self) -> None:
        """Test that concurrent reports don't lose data."""
        manager = ProgressManager()
        received: list[ToolProgress] = []
        lock = threading.Lock()

        def safe_append(p: ToolProgress) -> None:
            with lock:
                received.append(p)

        manager.set_callback(safe_append)

        def worker(worker_id: int) -> None:
            for i in range(100):
                progress = ToolProgress(
                    tool_name=f"worker_{worker_id}",
                    status_message=f"Progress {i}",
                    percent_complete=float(i),
                )
                manager.report(progress)

        # Run 5 workers concurrently
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(worker, i) for i in range(5)]
            for f in futures:
                f.result()

        # Should have received all 500 reports (5 workers * 100 reports each)
        assert len(received) == 500

    def test_concurrent_callback_changes(self) -> None:
        """Test that callback changes are thread-safe."""
        manager = ProgressManager()
        callback_changes = 0
        change_lock = threading.Lock()

        def increment() -> None:
            nonlocal callback_changes
            with change_lock:
                callback_changes += 1

        def callback_setter() -> None:
            for _ in range(100):
                manager.set_callback(lambda p: increment())
                time.sleep(0.0001)  # Small delay to increase contention
                manager.clear_callback()

        def reporter() -> None:
            for i in range(100):
                progress = ToolProgress(tool_name="reporter", status_message=f"Report {i}")
                manager.report(progress)
                time.sleep(0.0001)

        # Run setters and reporters concurrently
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [
                executor.submit(callback_setter),
                executor.submit(callback_setter),
                executor.submit(reporter),
                executor.submit(reporter),
            ]
            for f in futures:
                f.result()

        # No assertions on exact count - just verify no exceptions occurred


class TestGetProgressManager:
    """Tests for the get_progress_manager singleton function."""

    def setup_method(self) -> None:
        """Reset the singleton before each test."""
        reset_progress_manager()

    def teardown_method(self) -> None:
        """Clean up after each test."""
        reset_progress_manager()

    def test_returns_singleton(self) -> None:
        """Test that get_progress_manager returns the same instance."""
        manager1 = get_progress_manager()
        manager2 = get_progress_manager()

        assert manager1 is manager2

    def test_singleton_persists_callback(self) -> None:
        """Test that callback set on singleton persists."""
        received: list[ToolProgress] = []

        manager1 = get_progress_manager()
        manager1.set_callback(lambda p: received.append(p))

        manager2 = get_progress_manager()
        manager2.report(ToolProgress(tool_name="test", status_message="Hello"))

        assert len(received) == 1
        assert received[0].tool_name == "test"

    def test_reset_progress_manager(self) -> None:
        """Test that reset_progress_manager creates new instance."""
        manager1 = get_progress_manager()
        manager1.set_callback(lambda p: None)

        reset_progress_manager()

        manager2 = get_progress_manager()
        assert manager1 is not manager2
        assert manager2.get_callback() is None

    def test_concurrent_singleton_access(self) -> None:
        """Test that concurrent access to singleton is safe."""
        managers: list[ProgressManager] = []
        lock = threading.Lock()

        def get_manager() -> None:
            m = get_progress_manager()
            with lock:
                managers.append(m)

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(get_manager) for _ in range(100)]
            for f in futures:
                f.result()

        # All should be the same instance
        assert len(managers) == 100
        assert all(m is managers[0] for m in managers)
