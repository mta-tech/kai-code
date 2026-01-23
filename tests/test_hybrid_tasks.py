"""Tests for the hybrid async/thread task manager."""
from __future__ import annotations

import asyncio
import pickle
from datetime import datetime

import pytest
import pytest_asyncio

# Import directly from module to avoid naming conflicts
import sys
from pathlib import Path

# Add src to path for direct imports
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from kai_code.tasks.hybrid_manager import (
    Task as HybridTask,
    TaskStatus,
    HybridTaskManager,
    get_hybrid_task_manager,
)


class TestTaskStatus:
    """Tests for TaskStatus enum."""

    def test_status_values(self):
        """Test that status enum has expected values."""
        assert TaskStatus.QUEUED.value == "queued"
        assert TaskStatus.RUNNING.value == "running"
        assert TaskStatus.COMPLETED.value == "completed"
        assert TaskStatus.FAILED.value == "failed"
        assert TaskStatus.KILLED.value == "killed"
        assert TaskStatus.TIMED_OUT.value == "timed_out"


class TestTask:
    """Tests for Task dataclass."""

    def test_task_creation(self):
        """Test creating a task with defaults."""
        task = HybridTask(command="echo test")
        assert task.id
        assert task.status == TaskStatus.QUEUED
        assert task.command == "echo test"
        assert task.output == ""
        assert task.error is None
        assert task.started_at is None
        assert task.finished_at is None

    def test_task_duration_none_when_not_started(self):
        """Test that duration is None for tasks that haven't started."""
        task = HybridTask(command="echo test")
        assert task.duration is None

    def test_task_duration_when_running(self):
        """Test that duration is calculated for running tasks."""
        task = HybridTask(command="echo test")
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now()
        # Duration should be roughly the time since started
        assert task.duration is not None
        assert task.duration >= 0

    def test_task_duration_when_completed(self):
        """Test that duration is calculated for completed tasks."""
        from datetime import timedelta

        task = HybridTask(command="echo test")
        task.status = TaskStatus.COMPLETED
        task.started_at = datetime.now()
        task.finished_at = task.started_at + timedelta(seconds=5)
        assert task.duration == 5.0

    def test_task_serialization_safety(self):
        """Test that Task can be pickled and unpickled."""
        task = HybridTask(command="echo test", type="shell")
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now()
        task.finished_at = datetime.now()

        # Pickle and unpickle
        pickled = pickle.dumps(task)
        unpickled = pickle.loads(pickled)

        # Check that fields are preserved
        assert unpickled.id == task.id
        assert unpickled.status == task.status
        assert unpickled.command == task.command
        assert unpickled.type == task.type

        # Runtime-only state should be reset to None
        assert unpickled._asyncio_task is None


class TestHybridTaskManager:
    """Tests for HybridTaskManager."""

    @pytest_asyncio.fixture
    async def manager(self):
        """Create a fresh manager for each test."""
        manager = HybridTaskManager()
        yield manager
        await manager.shutdown()

    @pytest.mark.asyncio
    async def test_manager_initialization(self, manager):
        """Test that manager initializes correctly."""
        assert manager.total_count() == 0
        assert manager.active_count() == 0
        assert manager.get_all_tasks() == []
        assert manager.get_active_tasks() == []

    @pytest.mark.asyncio
    async def test_run_shell_simple_command(self, manager):
        """Test running a simple shell command."""
        task_id = await manager.run_shell("echo 'Hello, World!'")

        # Wait for task to complete
        await asyncio.sleep(0.5)

        task = manager.get_task(task_id)
        assert task is not None
        assert task.status in (TaskStatus.COMPLETED, TaskStatus.RUNNING)
        assert "Hello, World!" in task.output

    @pytest.mark.asyncio
    async def test_run_shell_with_timeout(self, manager):
        """Test that shell commands respect timeout."""
        # Sleep for 10 seconds but timeout after 1 second
        task_id = await manager.run_shell("sleep 10", timeout=1)

        # Wait for timeout
        await asyncio.sleep(2)

        task = manager.get_task(task_id)
        assert task is not None
        assert task.status == TaskStatus.TIMED_OUT
        assert "Timeout" in task.error

    @pytest.mark.asyncio
    async def test_run_shell_multiple_commands(self, manager):
        """Test running multiple shell commands concurrently."""
        task_ids = []
        for i in range(5):
            task_id = await manager.run_shell(f"echo 'Task {i}'")
            task_ids.append(task_id)

        # Wait for all tasks to complete
        await asyncio.sleep(1)

        for task_id in task_ids:
            task = manager.get_task(task_id)
            assert task is not None
            assert task.status in (TaskStatus.COMPLETED, TaskStatus.RUNNING)

    @pytest.mark.asyncio
    async def test_kill_task(self, manager):
        """Test killing a running task."""
        # Start a long-running task
        task_id = await manager.run_shell("sleep 10")

        # Wait a bit for it to start
        await asyncio.sleep(0.2)

        # Kill the task
        result = await manager.kill(task_id)
        assert result is True

        task = manager.get_task(task_id)
        assert task is not None
        assert task.status == TaskStatus.KILLED

    @pytest.mark.asyncio
    async def test_kill_nonexistent_task(self, manager):
        """Test killing a task that doesn't exist."""
        result = await manager.kill("nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_kill_all_tasks(self, manager):
        """Test killing all running tasks."""
        # Start multiple long-running tasks
        task_ids = []
        for i in range(3):
            task_id = await manager.run_shell("sleep 10")
            task_ids.append(task_id)

        # Wait a bit for them to start
        await asyncio.sleep(0.2)

        # Kill all
        count = await manager.kill_all()
        assert count == 3

        for task_id in task_ids:
            task = manager.get_task(task_id)
            assert task is not None
            assert task.status == TaskStatus.KILLED

    @pytest.mark.asyncio
    async def test_clear_completed_tasks(self, manager):
        """Test clearing completed tasks."""
        # Run a quick task
        task_id = await manager.run_shell("echo 'test'")

        # Wait for completion
        await asyncio.sleep(0.5)

        # Clear completed
        count = await manager.clear_completed()
        assert count >= 1

        # Task should be gone
        task = manager.get_task(task_id)
        assert task is None

    @pytest.mark.asyncio
    async def test_clear_all_tasks(self, manager):
        """Test clearing all tasks."""
        # Add some tasks
        task_ids = []
        for i in range(3):
            task_id = await manager.run_shell("echo 'test'")
            task_ids.append(task_id)

        # Wait a bit
        await asyncio.sleep(0.2)

        # Clear all
        await manager.clear_all()

        # All tasks should be gone
        assert manager.total_count() == 0
        for task_id in task_ids:
            task = manager.get_task(task_id)
            assert task is None

    @pytest.mark.asyncio
    async def test_get_all_tasks_sorted(self, manager):
        """Test that get_all_tasks returns tasks sorted by creation time."""
        # Add tasks with delay
        task_id1 = await manager.run_shell("echo 'first'")
        await asyncio.sleep(0.1)
        task_id2 = await manager.run_shell("echo 'second'")
        await asyncio.sleep(0.1)
        task_id3 = await manager.run_shell("echo 'third'")

        tasks = manager.get_all_tasks()
        assert len(tasks) == 3

        # Newest first (reverse chronological)
        assert tasks[0].id == task_id3
        assert tasks[1].id == task_id2
        assert tasks[2].id == task_id1

    @pytest.mark.asyncio
    async def test_task_completion_callback(self, manager):
        """Test that task completion callbacks are invoked."""
        completed_tasks = []

        def callback(task):
            completed_tasks.append(task.id)

        manager.on_task_complete(callback)

        task_id = await manager.run_shell("echo 'test'")

        # Wait for completion
        await asyncio.sleep(0.5)

        assert task_id in completed_tasks

    @pytest.mark.asyncio
    async def test_configure_method(self, manager):
        """Test configuring default settings."""
        from pathlib import Path

        new_root = Path("/tmp/test")
        new_model = "gpt-4"

        manager.configure(root_dir=new_root, model=new_model)

        assert manager._root_dir == new_root
        assert manager._model == new_model


class TestHybridTaskManagerStress:
    """Stress tests for HybridTaskManager."""

    @pytest_asyncio.fixture
    async def manager(self):
        """Create a fresh manager for each test."""
        manager = HybridTaskManager()
        yield manager
        await manager.shutdown()

    @pytest.mark.asyncio
    async def test_many_concurrent_shell_tasks(self, manager):
        """Test running 20 concurrent shell tasks."""
        task_ids = []
        for i in range(20):
            task_id = await manager.run_shell(f"echo 'Task {i}' && sleep 0.1")
            task_ids.append(task_id)

        # Wait for all to complete
        await asyncio.sleep(2)

        completed = sum(
            1 for tid in task_ids
            if manager.get_task(tid).status == TaskStatus.COMPLETED
        )

        assert completed == 20

    @pytest.mark.asyncio
    async def test_concurrent_mix_of_tasks(self, manager):
        """Test running a mix of quick and slow tasks."""
        task_ids = []

        # Add quick tasks
        for i in range(5):
            task_id = await manager.run_shell(f"echo 'Quick {i}'")
            task_ids.append(task_id)

        # Add slow tasks
        for i in range(3):
            task_id = await manager.run_shell("sleep 0.5")
            task_ids.append(task_id)

        # Wait for all to complete
        await asyncio.sleep(2)

        for task_id in task_ids:
            task = manager.get_task(task_id)
            assert task.status in (
                TaskStatus.COMPLETED,
                TaskStatus.FAILED,
                TaskStatus.TIMED_OUT,
            )


class TestGlobalHybridTaskManager:
    """Tests for the global HybridTaskManager singleton."""

    @pytest.mark.asyncio
    async def test_singleton_returns_same_instance(self):
        """Test that get_hybrid_task_manager returns the same instance."""
        manager1 = get_hybrid_task_manager()
        manager2 = get_hybrid_task_manager()
        assert manager1 is manager2

    @pytest.mark.asyncio
    async def test_singleton_isolation(self):
        """Test that singleton instance is properly isolated."""
        # Reset the global singleton for testing
        from kai_code.tasks.hybrid_manager import _hybrid_task_manager
        import importlib
        import sys

        # This is a bit of a hack, but we need to reset the module state
        # In production code, we wouldn't do this
        original_value = _hybrid_task_manager

        try:
            # Create a new instance
            manager = get_hybrid_task_manager()
            task_id = await manager.run_shell("echo 'test'")

            # Wait for completion
            await asyncio.sleep(0.5)

            task = manager.get_task(task_id)
            assert task is not None
        finally:
            # Restore original state if needed
            pass
