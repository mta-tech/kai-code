"""Auto-nudge integration tests for HybridTaskManager.

Tests the adapter that bridges new HybridTaskManager.Task with the
legacy TaskCompletionNotifier system.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# Add src to path for direct imports
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from kai_code.tasks.hybrid_manager import HybridTaskManager, TaskStatus
from kai_code.tasks.hybrid_notifier import (
    HybridTaskAdapter,
    HybridTaskCompletionNotifier,
)


class TestHybridTaskAdapter:
    """Tests for HybridTaskAdapter."""

    def test_adapter_provides_id(self):
        """Test adapter exposes task ID."""
        from kai_code.tasks.hybrid_manager import Task

        task = Task(id="test123", command="echo test")
        adapter = HybridTaskAdapter(task)

        assert adapter.id == "test123"

    def test_adapter_maps_command_to_description(self):
        """Test adapter maps command to description property."""
        from kai_code.tasks.hybrid_manager import Task

        task = Task(command="pytest tests/")
        adapter = HybridTaskAdapter(task)

        assert adapter.description == "pytest tests/"

    def test_adapter_exposes_type(self):
        """Test adapter exposes task type."""
        from kai_code.tasks.hybrid_manager import Task

        task = Task(type="shell")
        adapter = HybridTaskAdapter(task)

        assert adapter.type == "shell"

        task = Task(type="agent")
        adapter = HybridTaskAdapter(task)

        assert adapter.type == "agent"

    def test_adapter_wraps_status(self):
        """Test adapter wraps status with .value property."""
        from kai_code.tasks.hybrid_manager import Task

        task = Task(status=TaskStatus.COMPLETED)
        adapter = HybridTaskAdapter(task)

        assert adapter.status.value == "completed"

        task = Task(status=TaskStatus.FAILED)
        adapter = HybridTaskAdapter(task)

        assert adapter.status.value == "failed"

    def test_adapter_exposes_output(self):
        """Test adapter exposes task output."""
        from kai_code.tasks.hybrid_manager import Task

        task = Task(output="Hello, World!")
        adapter = HybridTaskAdapter(task)

        assert adapter.output == "Hello, World!"

    def test_adapter_exposes_error(self):
        """Test adapter exposes task error."""
        from kai_code.tasks.hybrid_manager import Task

        task = Task(error="Command failed")
        adapter = HybridTaskAdapter(task)

        assert adapter.error == "Command failed"

    def test_adapter_exposes_duration(self):
        """Test adapter exposes task duration."""
        from kai_code.tasks.hybrid_manager import Task
        from datetime import datetime, timedelta

        started = datetime.now()
        finished = started + timedelta(seconds=5.5)

        task = Task(started_at=started, finished_at=finished)
        adapter = HybridTaskAdapter(task)

        assert adapter.duration == 5.5

    def test_adapter_returns_none_for_missing_duration(self):
        """Test adapter returns None when duration unavailable."""
        from kai_code.tasks.hybrid_manager import Task

        task = Task()  # No started_at/finished_at
        adapter = HybridTaskAdapter(task)

        assert adapter.duration is None


class TestHybridTaskCompletionNotifier:
    """Tests for HybridTaskCompletionNotifier."""

    def test_notifier_delegates_to_legacy_notifier(self):
        """Test notifier delegates to legacy notifier with adapted task."""
        from kai_code.tasks.hybrid_manager import Task

        # Create mock legacy notifier
        legacy_notifier = MagicMock()

        # Create hybrid notifier
        notifier = HybridTaskCompletionNotifier(legacy_notifier)

        # Create a new-style task
        task = Task(
            id="abc123",
            command="echo test",
            type="shell",
            status=TaskStatus.COMPLETED,
            output="test\n",
        )

        # Call the notifier
        notifier(task)

        # Verify legacy notifier was called with adapted task
        legacy_notifier.assert_called_once()
        adapted_task = legacy_notifier.call_args[0][0]

        # Verify the adapted task has the right interface
        assert adapted_task.id == "abc123"
        assert adapted_task.description == "echo test"
        assert adapted_task.type == "shell"
        assert adapted_task.status.value == "completed"
        assert adapted_task.output == "test\n"

    def test_notifier_handles_task_with_error(self):
        """Test notifier properly passes through error messages."""
        from kai_code.tasks.hybrid_manager import Task

        legacy_notifier = MagicMock()
        notifier = HybridTaskCompletionNotifier(legacy_notifier)

        task = Task(
            id="fail123",
            command="false",
            status=TaskStatus.FAILED,
            error="Command exited with status 1",
        )

        notifier(task)

        adapted_task = legacy_notifier.call_args[0][0]
        assert adapted_task.error == "Command exited with status 1"


class TestHybridTaskManagerCallbackRegistration:
    """Tests for callback registration in get_hybrid_task_manager."""

    @pytest.mark.asyncio
    async def test_callback_invoked_on_task_completion(self):
        """Test that callback is invoked when a task completes."""
        # Create a fresh manager
        manager = HybridTaskManager()

        # Track callback invocations
        callback_invoked = []

        def mock_callback(task):
            callback_invoked.append(task)

        manager.on_task_complete(mock_callback)

        # Run a task
        task_id = await manager.run_shell("echo 'test output'")
        await asyncio.sleep(1)  # Wait for completion

        # Verify callback was invoked
        assert len(callback_invoked) == 1
        assert callback_invoked[0].id == task_id
        assert callback_invoked[0].output == "test output\n"

    @pytest.mark.asyncio
    async def test_callback_with_notifier_integration(self):
        """Test full integration with notifier (end-to-end)."""
        from kai_code.tasks.hybrid_notifier import HybridTaskCompletionNotifier
        from kai_code.tasks.hybrid_manager import get_hybrid_task_manager

        # Create a mock legacy notifier
        legacy_calls = []

        class MockLegacyNotifier:
            def __call__(self, adapted_task):
                legacy_calls.append({
                    "id": adapted_task.id,
                    "description": adapted_task.description,
                    "type": adapted_task.type,
                    "status": adapted_task.status.value,
                    "output": adapted_task.output,
                })

        # Get manager and register callback
        manager = get_hybrid_task_manager()
        mock_notifier = MockLegacyNotifier()
        hybrid_notifier = HybridTaskCompletionNotifier(mock_notifier)
        manager.on_task_complete(hybrid_notifier)

        # Run a task
        task_id = await manager.run_shell("echo 'integration test'")
        await asyncio.sleep(1)  # Wait for completion

        # Verify legacy notifier was called with adapted task
        assert len(legacy_calls) == 1
        call = legacy_calls[0]
        assert call["id"] == task_id
        assert call["description"] == "echo 'integration test'"
        assert call["type"] == "shell"
        assert call["status"] == "completed"
        assert "integration test" in call["output"]

        await manager.shutdown()
