"""Integration tests for progress reporting across tools.

These tests verify that progress reporting works end-to-end for
web_search, http_request, fetch_url, and file operations. Network calls
are mocked to avoid external dependencies.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from kai_code.progress import (
    ProgressPhase,
    ToolProgress,
    get_progress_manager,
    reset_progress_manager,
)


class TestWebSearchProgressIntegration:
    """Integration tests for web_search progress reporting."""

    def setup_method(self) -> None:
        """Reset the progress manager before each test."""
        reset_progress_manager()

    def teardown_method(self) -> None:
        """Clean up after each test."""
        reset_progress_manager()

    def test_web_search_reports_all_phases(self) -> None:
        """Test that web_search reports progress through all expected phases."""
        received: list[ToolProgress] = []
        manager = get_progress_manager()
        manager.set_callback(lambda p: received.append(p))

        # Mock the Tavily client and rich_settings
        mock_client = MagicMock()
        mock_client.search.return_value = {
            "results": [
                {"title": "Result 1", "url": "https://example.com", "content": "Content 1"},
                {"title": "Result 2", "url": "https://example.org", "content": "Content 2"},
            ]
        }

        with patch("kai_code.tools.web.rich_settings") as mock_settings:
            mock_settings.has_tavily = True
            mock_settings.tavily_api_key = "test-key"

            with patch("tavily.TavilyClient", return_value=mock_client):
                from kai_code.tools.web import web_search

                result = web_search("test query", max_results=5)

        # Verify we got results
        assert "results" in result
        assert len(result["results"]) == 2

        # Verify all phases were reported
        assert len(received) >= 4

        # Check phases in order
        phases = [p.phase for p in received]
        assert ProgressPhase.STARTING in phases
        assert ProgressPhase.CONNECTING in phases
        assert ProgressPhase.PROCESSING in phases
        assert ProgressPhase.COMPLETE in phases

        # Verify messages contain expected content
        messages = [p.status_message for p in received]
        assert any("test query" in m for m in messages)
        assert any("Tavily" in m for m in messages)
        assert any("2 results" in m or "Processing" in m for m in messages)

    def test_web_search_no_tavily_key(self) -> None:
        """Test web_search progress when Tavily is not configured."""
        received: list[ToolProgress] = []
        manager = get_progress_manager()
        manager.set_callback(lambda p: received.append(p))

        with patch("kai_code.tools.web.rich_settings") as mock_settings:
            mock_settings.has_tavily = False

            from kai_code.tools.web import web_search

            result = web_search("test query")

        # Should still report starting phase
        assert len(received) >= 1
        assert received[0].phase == ProgressPhase.STARTING
        assert "test query" in received[0].status_message

        # Should return error
        assert "error" in result

    def test_web_search_tool_name(self) -> None:
        """Test that web_search reports correct tool name."""
        received: list[ToolProgress] = []
        manager = get_progress_manager()
        manager.set_callback(lambda p: received.append(p))

        with patch("kai_code.tools.web.rich_settings") as mock_settings:
            mock_settings.has_tavily = False

            from kai_code.tools.web import web_search

            web_search("test")

        assert all(p.tool_name == "web_search" for p in received)


class TestHttpRequestProgressIntegration:
    """Integration tests for http_request progress reporting."""

    def setup_method(self) -> None:
        """Reset the progress manager before each test."""
        reset_progress_manager()

    def teardown_method(self) -> None:
        """Clean up after each test."""
        reset_progress_manager()

    def test_http_request_reports_all_phases(self) -> None:
        """Test that http_request reports progress through all expected phases."""
        received: list[ToolProgress] = []
        manager = get_progress_manager()
        manager.set_callback(lambda p: received.append(p))

        # Create a mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.json.return_value = {"data": "test"}
        mock_response.url = "https://api.example.com/test"

        with patch("kai_code.tools.web.requests.request", return_value=mock_response):
            from kai_code.tools.web import http_request

            result = http_request("https://api.example.com/test", method="GET")

        # Verify success
        assert result["success"] is True
        assert result["status_code"] == 200

        # Verify all phases were reported
        assert len(received) >= 4

        phases = [p.phase for p in received]
        assert ProgressPhase.STARTING in phases
        assert ProgressPhase.CONNECTING in phases
        assert ProgressPhase.DOWNLOADING in phases
        assert ProgressPhase.COMPLETE in phases

        # Verify messages contain expected content
        messages = [p.status_message for p in received]
        assert any("api.example.com" in m for m in messages)
        assert any("GET" in m for m in messages)
        assert any("200" in m for m in messages)

    def test_http_request_post_method(self) -> None:
        """Test http_request progress with POST method."""
        received: list[ToolProgress] = []
        manager = get_progress_manager()
        manager.set_callback(lambda p: received.append(p))

        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.headers = {}
        mock_response.json.return_value = {"created": True}
        mock_response.url = "https://api.example.com/create"

        with patch("kai_code.tools.web.requests.request", return_value=mock_response):
            from kai_code.tools.web import http_request

            result = http_request(
                "https://api.example.com/create",
                method="POST",
                data={"name": "test"},
            )

        assert result["success"] is True
        assert result["status_code"] == 201

        # Verify POST appears in messages
        messages = [p.status_message for p in received]
        assert any("POST" in m for m in messages)

    def test_http_request_timeout_error(self) -> None:
        """Test http_request progress when timeout occurs."""
        import requests

        received: list[ToolProgress] = []
        manager = get_progress_manager()
        manager.set_callback(lambda p: received.append(p))

        with patch(
            "kai_code.tools.web.requests.request",
            side_effect=requests.exceptions.Timeout("Connection timed out"),
        ):
            from kai_code.tools.web import http_request

            result = http_request("https://slow.example.com", timeout=5)

        # Should report error
        assert result["success"] is False
        assert "timed out" in result["content"]

        # Should still report phases
        phases = [p.phase for p in received]
        assert ProgressPhase.STARTING in phases
        assert ProgressPhase.CONNECTING in phases
        assert ProgressPhase.COMPLETE in phases

        # Should report timeout in message
        messages = [p.status_message for p in received]
        assert any("timed out" in m.lower() for m in messages)

    def test_http_request_connection_error(self) -> None:
        """Test http_request progress when connection fails."""
        import requests

        received: list[ToolProgress] = []
        manager = get_progress_manager()
        manager.set_callback(lambda p: received.append(p))

        with patch(
            "kai_code.tools.web.requests.request",
            side_effect=requests.exceptions.ConnectionError("Failed to connect"),
        ):
            from kai_code.tools.web import http_request

            result = http_request("https://invalid.example.com")

        assert result["success"] is False

        # Should complete with error phase
        phases = [p.phase for p in received]
        assert ProgressPhase.COMPLETE in phases

        messages = [p.status_message for p in received]
        assert any("error" in m.lower() for m in messages)

    def test_http_request_tool_name(self) -> None:
        """Test that http_request reports correct tool name."""
        received: list[ToolProgress] = []
        manager = get_progress_manager()
        manager.set_callback(lambda p: received.append(p))

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.json.return_value = {}
        mock_response.url = "https://example.com"

        with patch("kai_code.tools.web.requests.request", return_value=mock_response):
            from kai_code.tools.web import http_request

            http_request("https://example.com")

        assert all(p.tool_name == "http_request" for p in received)


class TestFetchUrlProgressIntegration:
    """Integration tests for fetch_url progress reporting."""

    def setup_method(self) -> None:
        """Reset the progress manager before each test."""
        reset_progress_manager()

    def teardown_method(self) -> None:
        """Clean up after each test."""
        reset_progress_manager()

    def test_fetch_url_reports_all_phases(self) -> None:
        """Test that fetch_url reports progress through all expected phases."""
        received: list[ToolProgress] = []
        manager = get_progress_manager()
        manager.set_callback(lambda p: received.append(p))

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "<html><body><h1>Hello World</h1></body></html>"
        mock_response.url = "https://example.com/page"
        mock_response.raise_for_status = MagicMock()

        with patch("kai_code.tools.web.requests.get", return_value=mock_response):
            from kai_code.tools.web import fetch_url

            result = fetch_url("https://example.com/page")

        # Verify success
        assert "markdown_content" in result
        assert result["status_code"] == 200

        # Verify phases
        phases = [p.phase for p in received]
        assert ProgressPhase.STARTING in phases
        assert ProgressPhase.PROCESSING in phases
        assert ProgressPhase.COMPLETE in phases

        # Verify messages
        messages = [p.status_message for p in received]
        assert any("example.com" in m for m in messages)
        assert any("markdown" in m.lower() or "Converting" in m for m in messages)
        assert any("characters" in m.lower() or "Processed" in m for m in messages)

    def test_fetch_url_timeout_error(self) -> None:
        """Test fetch_url progress when timeout occurs."""
        import requests

        received: list[ToolProgress] = []
        manager = get_progress_manager()
        manager.set_callback(lambda p: received.append(p))

        with patch(
            "kai_code.tools.web.requests.get",
            side_effect=requests.exceptions.Timeout("Request timed out"),
        ):
            from kai_code.tools.web import fetch_url

            result = fetch_url("https://slow.example.com", timeout=10)

        assert "error" in result

        phases = [p.phase for p in received]
        assert ProgressPhase.STARTING in phases
        assert ProgressPhase.COMPLETE in phases

    def test_fetch_url_tool_name(self) -> None:
        """Test that fetch_url reports correct tool name."""
        import requests

        received: list[ToolProgress] = []
        manager = get_progress_manager()
        manager.set_callback(lambda p: received.append(p))

        with patch(
            "kai_code.tools.web.requests.get",
            side_effect=requests.exceptions.ConnectionError("Failed"),
        ):
            from kai_code.tools.web import fetch_url

            fetch_url("https://example.com")

        assert all(p.tool_name == "fetch_url" for p in received)


class TestLargeFileReadProgressIntegration:
    """Integration tests for large file read progress reporting."""

    def setup_method(self) -> None:
        """Reset the progress manager before each test."""
        reset_progress_manager()

    def teardown_method(self) -> None:
        """Clean up after each test."""
        reset_progress_manager()

    def test_large_file_reports_progress(self) -> None:
        """Test that reading a large file reports progress."""
        received: list[ToolProgress] = []
        manager = get_progress_manager()
        manager.set_callback(lambda p: received.append(p))

        # Create a temporary directory with a large file (>50KB)
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            large_file = tmppath / "large_file.txt"

            # Create a file larger than LARGE_FILE_THRESHOLD_BYTES (50KB)
            # Each line is ~100 characters, so we need >500 lines for >50KB
            large_content = "\n".join([f"Line {i}: " + "x" * 90 for i in range(600)])
            large_file.write_text(large_content)

            # Verify file is large enough
            assert large_file.stat().st_size >= 50 * 1024

            # Create backend and read file
            from kai_code.backend import KaiLocalBackend

            backend = KaiLocalBackend(root_dir=tmppath)
            result = backend.read("/large_file.txt")

        # Should have received progress reports
        assert len(received) >= 2

        # Verify phases
        phases = [p.phase for p in received]
        assert ProgressPhase.STARTING in phases
        assert ProgressPhase.COMPLETE in phases

        # Verify tool name
        assert all(p.tool_name == "read_file" for p in received)

        # Verify messages
        messages = [p.status_message for p in received]
        assert any("Reading" in m for m in messages)
        assert any("lines" in m.lower() for m in messages)

        # Verify percentages
        percents = [p.percent_complete for p in received if p.percent_complete is not None]
        assert 0.0 in percents
        assert 100.0 in percents

    def test_small_file_no_progress(self) -> None:
        """Test that reading a small file does not report progress."""
        received: list[ToolProgress] = []
        manager = get_progress_manager()
        manager.set_callback(lambda p: received.append(p))

        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            small_file = tmppath / "small_file.txt"

            # Create a small file (<50KB)
            small_content = "This is a small file.\n" * 10
            small_file.write_text(small_content)

            # Verify file is small
            assert small_file.stat().st_size < 50 * 1024

            from kai_code.backend import KaiLocalBackend

            backend = KaiLocalBackend(root_dir=tmppath)
            backend.read("/small_file.txt")

        # Should not report progress for small files
        assert len(received) == 0


class TestGlobProgressIntegration:
    """Integration tests for glob progress reporting."""

    def setup_method(self) -> None:
        """Reset the progress manager before each test."""
        reset_progress_manager()

    def teardown_method(self) -> None:
        """Clean up after each test."""
        reset_progress_manager()

    def test_glob_reports_progress(self) -> None:
        """Test that glob operation reports progress."""
        received: list[ToolProgress] = []
        manager = get_progress_manager()
        manager.set_callback(lambda p: received.append(p))

        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            # Create some test files
            (tmppath / "file1.py").write_text("# python file 1")
            (tmppath / "file2.py").write_text("# python file 2")
            (tmppath / "file3.txt").write_text("text file")

            from kai_code.backend import KaiLocalBackend

            backend = KaiLocalBackend(root_dir=tmppath)
            result = backend.glob_info("*.py")

        # Should have progress reports
        assert len(received) >= 2

        # Verify phases
        phases = [p.phase for p in received]
        assert ProgressPhase.STARTING in phases
        assert ProgressPhase.COMPLETE in phases

        # Verify tool name
        assert all(p.tool_name == "glob" for p in received)

        # Verify messages mention the pattern
        messages = [p.status_message for p in received]
        assert any("*.py" in m for m in messages)
        assert any("matching" in m.lower() or "Found" in m for m in messages)

    def test_glob_reports_match_count(self) -> None:
        """Test that glob reports the correct match count."""
        received: list[ToolProgress] = []
        manager = get_progress_manager()
        manager.set_callback(lambda p: received.append(p))

        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            # Create 5 Python files
            for i in range(5):
                (tmppath / f"file{i}.py").write_text(f"# file {i}")

            from kai_code.backend import KaiLocalBackend

            backend = KaiLocalBackend(root_dir=tmppath)
            result = backend.glob_info("*.py")

        # Find the completion message
        complete_msgs = [
            p.status_message for p in received if p.phase == ProgressPhase.COMPLETE
        ]
        assert len(complete_msgs) > 0
        assert any("5" in m for m in complete_msgs)


class TestGrepProgressIntegration:
    """Integration tests for grep progress reporting."""

    def setup_method(self) -> None:
        """Reset the progress manager before each test."""
        reset_progress_manager()

    def teardown_method(self) -> None:
        """Clean up after each test."""
        reset_progress_manager()

    def test_grep_reports_progress(self) -> None:
        """Test that grep operation reports progress."""
        received: list[ToolProgress] = []
        manager = get_progress_manager()
        manager.set_callback(lambda p: received.append(p))

        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            # Create test files with searchable content
            (tmppath / "file1.py").write_text("def hello_world():\n    pass\n")
            (tmppath / "file2.py").write_text("def goodbye_world():\n    pass\n")

            from kai_code.backend import KaiLocalBackend

            backend = KaiLocalBackend(root_dir=tmppath)
            result = backend.grep_raw("hello", glob="*.py")

        # Should have progress reports
        assert len(received) >= 2

        # Verify phases
        phases = [p.phase for p in received]
        assert ProgressPhase.STARTING in phases
        assert ProgressPhase.COMPLETE in phases

        # Verify tool name
        assert all(p.tool_name == "grep" for p in received)

        # Verify messages mention the pattern
        messages = [p.status_message for p in received]
        assert any("hello" in m for m in messages)

    def test_grep_truncates_long_patterns(self) -> None:
        """Test that grep truncates long patterns in progress messages."""
        received: list[ToolProgress] = []
        manager = get_progress_manager()
        manager.set_callback(lambda p: received.append(p))

        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            (tmppath / "test.txt").write_text("some content")

            # Long pattern (>30 chars)
            long_pattern = "a" * 50

            from kai_code.backend import KaiLocalBackend

            backend = KaiLocalBackend(root_dir=tmppath)
            backend.grep_raw(long_pattern, glob="*.txt")

        # Find starting message
        start_msgs = [
            p.status_message for p in received if p.phase == ProgressPhase.STARTING
        ]
        assert len(start_msgs) > 0

        # Should be truncated with ellipsis
        for msg in start_msgs:
            # Either the full pattern shouldn't appear or it should be truncated
            if long_pattern in msg:
                pytest.fail("Long pattern should be truncated")
            if "..." in msg:
                break
        else:
            # Pattern should contain ellipsis for truncation
            assert any("..." in msg for msg in start_msgs)


class TestProgressCallbackIntegration:
    """Integration tests for progress callback behavior."""

    def setup_method(self) -> None:
        """Reset the progress manager before each test."""
        reset_progress_manager()

    def teardown_method(self) -> None:
        """Clean up after each test."""
        reset_progress_manager()

    def test_no_callback_no_error(self) -> None:
        """Test that tools work correctly when no callback is set."""
        # Don't set any callback
        manager = get_progress_manager()
        assert manager.get_callback() is None

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.json.return_value = {"ok": True}
        mock_response.url = "https://example.com"

        with patch("kai_code.tools.web.requests.request", return_value=mock_response):
            from kai_code.tools.web import http_request

            # Should not raise any error
            result = http_request("https://example.com")

        assert result["success"] is True

    def test_callback_exception_ignored(self) -> None:
        """Test that exceptions in callbacks don't disrupt tool execution."""
        def bad_callback(progress: ToolProgress) -> None:
            raise RuntimeError("Callback error!")

        manager = get_progress_manager()
        manager.set_callback(bad_callback)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.json.return_value = {"ok": True}
        mock_response.url = "https://example.com"

        with patch("kai_code.tools.web.requests.request", return_value=mock_response):
            from kai_code.tools.web import http_request

            # Should not raise, callback exception should be silently ignored
            result = http_request("https://example.com")

        assert result["success"] is True

    def test_callback_receives_correct_types(self) -> None:
        """Test that callbacks receive properly typed ToolProgress objects."""
        received: list[ToolProgress] = []

        def type_checking_callback(progress: ToolProgress) -> None:
            # Verify it's actually a ToolProgress
            assert isinstance(progress, ToolProgress)
            assert isinstance(progress.tool_name, str)
            assert isinstance(progress.status_message, str)
            if progress.phase is not None:
                assert isinstance(progress.phase, ProgressPhase)
            if progress.percent_complete is not None:
                assert isinstance(progress.percent_complete, float)
            received.append(progress)

        manager = get_progress_manager()
        manager.set_callback(type_checking_callback)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.json.return_value = {}
        mock_response.url = "https://example.com"

        with patch("kai_code.tools.web.requests.request", return_value=mock_response):
            from kai_code.tools.web import http_request

            http_request("https://example.com")

        # Should have received multiple progress updates
        assert len(received) >= 4


class TestProgressScopeIntegration:
    """Integration tests for progress_scope context manager."""

    def setup_method(self) -> None:
        """Reset the progress manager before each test."""
        reset_progress_manager()

    def teardown_method(self) -> None:
        """Clean up after each test."""
        reset_progress_manager()

    def test_scoped_callback_isolation(self) -> None:
        """Test that progress_scope properly isolates callbacks."""
        outer_received: list[ToolProgress] = []
        inner_received: list[ToolProgress] = []

        manager = get_progress_manager()
        manager.set_callback(lambda p: outer_received.append(p))

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.json.return_value = {}
        mock_response.url = "https://example.com"

        # First request goes to outer callback
        with patch("kai_code.tools.web.requests.request", return_value=mock_response):
            from kai_code.tools.web import http_request

            http_request("https://example.com/outer")

        outer_count_before = len(outer_received)

        # Request inside scope goes to inner callback
        with manager.progress_scope(lambda p: inner_received.append(p)):
            with patch("kai_code.tools.web.requests.request", return_value=mock_response):
                http_request("https://example.com/inner")

        # Verify inner callback received the progress
        assert len(inner_received) >= 4

        # Verify outer callback didn't receive progress from inner scope
        assert len(outer_received) == outer_count_before

        # Request after scope goes to outer callback again
        with patch("kai_code.tools.web.requests.request", return_value=mock_response):
            http_request("https://example.com/outer2")

        assert len(outer_received) > outer_count_before
