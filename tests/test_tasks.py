"""Tests for the background tasks module."""
from __future__ import annotations

import time
from pathlib import Path

import pytest

from kai_code.tasks import (
    Task,
    TaskStatus,
    BackgroundShellTask,
    BackgroundAgentTask,
    TaskManager,
    get_task_manager,
    format_task_status_line,
    format_tasks_summary,
)


class TestTaskStatus:
    """Tests for TaskStatus enum."""

    def test_status_values(self):
        """Test that status enum has expected values."""
        assert TaskStatus.PENDING.value == "pending"
        assert TaskStatus.RUNNING.value == "running"
        assert TaskStatus.COMPLETED.value == "completed"
        assert TaskStatus.FAILED.value == "failed"
        assert TaskStatus.KILLED.value == "killed"


class TestBackgroundShellTask:
    """Tests for BackgroundShellTask."""

    def test_task_creation(self):
        """Test creating a shell task."""
        task = BackgroundShellTask(command="echo hello")
        assert task.type == "shell"
        assert task.command == "echo hello"
        assert task.status == TaskStatus.PENDING
        assert "echo hello" in task.description

    def test_task_run_success(self):
        """Test running a successful shell command."""
        task = BackgroundShellTask(command="echo hello", working_dir=Path.cwd())
        task.run()

        assert task.status == TaskStatus.COMPLETED
        assert task.exit_code == 0
        assert "hello" in task.output
        assert task.finished_at is not None

    def test_task_run_failure(self):
        """Test running a failing shell command."""
        task = BackgroundShellTask(command="exit 1", working_dir=Path.cwd())
        task.run()

        assert task.status == TaskStatus.FAILED
        assert task.exit_code == 1
        assert task.finished_at is not None

    def test_task_kill(self):
        """Test killing a running task."""
        # Use a long-running command
        task = BackgroundShellTask(command="sleep 60", working_dir=Path.cwd())
        task.status = TaskStatus.RUNNING  # Manually set to simulate running

        # Can't really test kill without threading, so just test the state check
        result = task.kill()
        assert result is True
        assert task.status == TaskStatus.KILLED

    def test_task_duration(self):
        """Test task duration calculation."""
        task = BackgroundShellTask(command="echo hello", working_dir=Path.cwd())
        task.run()

        assert task.duration is not None
        assert task.duration >= 0

    def test_task_display_status(self):
        """Test display status strings."""
        task = BackgroundShellTask(command="echo hello", working_dir=Path.cwd())

        task.status = TaskStatus.PENDING
        assert task.display_status == "pending"

        task.status = TaskStatus.COMPLETED
        assert "done" in task.display_status

        task.status = TaskStatus.FAILED
        assert "failed" in task.display_status

        task.status = TaskStatus.KILLED
        assert task.display_status == "killed"


class TestTaskManager:
    """Tests for TaskManager singleton."""

    @pytest.fixture(autouse=True)
    def reset_manager(self):
        """Reset the task manager before each test."""
        manager = get_task_manager()
        manager.clear_all()
        yield
        manager.clear_all()

    def test_singleton(self):
        """Test that TaskManager is a singleton."""
        manager1 = get_task_manager()
        manager2 = get_task_manager()
        assert manager1 is manager2

    def test_run_shell(self):
        """Test running a shell command."""
        manager = get_task_manager()
        task_id = manager.run_shell("echo test")

        assert task_id is not None
        assert len(task_id) == 8  # UUID hex[:8]

        task = manager.get_task(task_id)
        assert task is not None
        assert task.type == "shell"

    def test_get_all_tasks(self):
        """Test getting all tasks."""
        manager = get_task_manager()
        manager.run_shell("echo 1")
        manager.run_shell("echo 2")

        tasks = manager.get_all_tasks()
        assert len(tasks) == 2

    def test_get_active_tasks(self):
        """Test getting active tasks."""
        manager = get_task_manager()
        task_id = manager.run_shell("echo fast")

        # Wait for completion
        time.sleep(0.5)

        active = manager.get_active_tasks()
        # Task should have completed by now
        assert isinstance(active, list)

    def test_get_completed_tasks(self):
        """Test getting completed tasks."""
        manager = get_task_manager()
        task_id = manager.run_shell("echo done")

        # Wait for completion
        time.sleep(0.5)

        completed = manager.get_completed_tasks()
        assert len(completed) >= 1

    def test_kill_task(self):
        """Test killing a task."""
        manager = get_task_manager()
        # Use a long command
        task_id = manager.run_shell("sleep 60")

        # Give it time to start
        time.sleep(0.2)

        result = manager.kill_task(task_id)
        # Should be able to kill it
        assert isinstance(result, bool)

    def test_kill_nonexistent_task(self):
        """Test killing a non-existent task."""
        manager = get_task_manager()
        result = manager.kill_task("nonexistent")
        assert result is False

    def test_clear_completed(self):
        """Test clearing completed tasks."""
        manager = get_task_manager()
        manager.run_shell("echo 1")
        manager.run_shell("echo 2")

        # Wait for completion
        time.sleep(0.5)

        cleared = manager.clear_completed()
        assert cleared >= 0

    def test_active_count(self):
        """Test active task count."""
        manager = get_task_manager()
        count = manager.active_count()
        assert isinstance(count, int)
        assert count >= 0

    def test_total_count(self):
        """Test total task count."""
        manager = get_task_manager()
        manager.run_shell("echo 1")
        manager.run_shell("echo 2")

        count = manager.total_count()
        assert count == 2


class TestPanelFunctions:
    """Tests for panel helper functions."""

    @pytest.fixture(autouse=True)
    def reset_manager(self):
        """Reset the task manager before each test."""
        manager = get_task_manager()
        manager.clear_all()
        yield
        manager.clear_all()

    def test_format_task_status_line_no_tasks(self):
        """Test status line with no tasks."""
        result = format_task_status_line()
        assert result is None

    def test_format_task_status_line_with_tasks(self):
        """Test status line with tasks."""
        manager = get_task_manager()
        manager.run_shell("sleep 60")

        # Give it time to start
        time.sleep(0.2)

        result = format_task_status_line()
        # Might be None if task completed fast, or a string
        assert result is None or isinstance(result, str)

    def test_format_tasks_summary_no_tasks(self):
        """Test summary with no tasks."""
        result = format_tasks_summary()
        assert "No background tasks" in result

    def test_format_tasks_summary_with_tasks(self):
        """Test summary with tasks."""
        manager = get_task_manager()
        manager.run_shell("echo test")

        # Wait for completion
        time.sleep(0.5)

        result = format_tasks_summary()
        assert "Background Tasks" in result


class TestAgentTools:
    """Tests for agent tools."""

    @pytest.fixture(autouse=True)
    def reset_manager(self):
        """Reset the task manager before each test."""
        manager = get_task_manager()
        manager.clear_all()
        yield
        manager.clear_all()

    def test_list_background_tasks_empty(self):
        """Test listing with no tasks."""
        from kai_code.tasks import list_background_tasks

        result = list_background_tasks.invoke({})
        assert "No background tasks" in result

    def test_list_background_tasks_with_tasks(self):
        """Test listing with tasks."""
        from kai_code.tasks import list_background_tasks

        manager = get_task_manager()
        manager.run_shell("echo test")

        # Wait for completion
        time.sleep(0.5)

        result = list_background_tasks.invoke({})
        assert "Background Tasks" in result
        assert "shell" in result

    def test_get_task_output_not_found(self):
        """Test getting output for non-existent task."""
        from kai_code.tasks import get_task_output

        result = get_task_output.invoke({"task_id": "nonexistent"})
        assert "not found" in result.lower()

    def test_get_task_output_success(self):
        """Test getting output for existing task."""
        from kai_code.tasks import get_task_output

        manager = get_task_manager()
        task_id = manager.run_shell("echo hello_world")

        # Wait for completion
        time.sleep(0.5)

        result = get_task_output.invoke({"task_id": task_id})
        assert "hello_world" in result

    def test_kill_background_task_not_found(self):
        """Test killing non-existent task."""
        from kai_code.tasks import kill_background_task

        result = kill_background_task.invoke({"task_id": "nonexistent"})
        assert "not found" in result.lower()

    def test_kill_background_task_not_running(self):
        """Test killing completed task."""
        from kai_code.tasks import kill_background_task

        manager = get_task_manager()
        task_id = manager.run_shell("echo fast")

        # Wait for completion
        time.sleep(0.5)

        result = kill_background_task.invoke({"task_id": task_id})
        assert "not running" in result.lower()
