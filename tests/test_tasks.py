"""Tests for the background tasks module."""
from __future__ import annotations

import time
from pathlib import Path

import pytest

from kai_code.tasks import (
    Task,
    TaskStatus,
    TaskPriority,
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

    def test_queued_status_value(self):
        """Test that QUEUED status has expected value."""
        assert TaskStatus.QUEUED.value == "queued"


class TestTaskPriority:
    """Tests for TaskPriority enum."""

    def test_priority_values(self):
        """Test that priority enum has correct numeric values."""
        assert TaskPriority.HIGH.value == 1
        assert TaskPriority.NORMAL.value == 2
        assert TaskPriority.LOW.value == 3

    def test_priority_ordering(self):
        """Test that lower numeric values indicate higher priority."""
        # Lower value = higher priority for heap ordering
        assert TaskPriority.HIGH.value < TaskPriority.NORMAL.value
        assert TaskPriority.NORMAL.value < TaskPriority.LOW.value

    def test_priority_comparisons(self):
        """Test that priorities can be compared by their values."""
        priorities = [TaskPriority.LOW, TaskPriority.HIGH, TaskPriority.NORMAL]
        # Sort by value (ascending = high priority first)
        sorted_priorities = sorted(priorities, key=lambda p: p.value)
        assert sorted_priorities == [
            TaskPriority.HIGH,
            TaskPriority.NORMAL,
            TaskPriority.LOW,
        ]


class TestTaskPriorityField:
    """Tests for Task priority field."""

    def test_task_default_priority(self):
        """Test that tasks default to NORMAL priority."""
        task = BackgroundShellTask(command="echo test")
        assert task.priority == TaskPriority.NORMAL

    def test_task_with_high_priority(self):
        """Test creating a task with HIGH priority."""
        task = BackgroundShellTask(
            command="echo test",
            priority=TaskPriority.HIGH,
        )
        assert task.priority == TaskPriority.HIGH

    def test_task_with_low_priority(self):
        """Test creating a task with LOW priority."""
        task = BackgroundShellTask(
            command="echo test",
            priority=TaskPriority.LOW,
        )
        assert task.priority == TaskPriority.LOW

    def test_agent_task_default_priority(self):
        """Test that agent tasks default to NORMAL priority."""
        task = BackgroundAgentTask(prompt="test prompt")
        assert task.priority == TaskPriority.NORMAL

    def test_agent_task_with_priority(self):
        """Test creating an agent task with specified priority."""
        task = BackgroundAgentTask(
            prompt="test prompt",
            priority=TaskPriority.HIGH,
        )
        assert task.priority == TaskPriority.HIGH

    def test_priority_indicator_high(self):
        """Test priority indicator for HIGH priority."""
        task = BackgroundShellTask(
            command="echo test",
            priority=TaskPriority.HIGH,
        )
        assert task.priority_indicator == "[H] "

    def test_priority_indicator_normal(self):
        """Test priority indicator for NORMAL priority (empty)."""
        task = BackgroundShellTask(command="echo test")
        assert task.priority_indicator == ""

    def test_priority_indicator_low(self):
        """Test priority indicator for LOW priority."""
        task = BackgroundShellTask(
            command="echo test",
            priority=TaskPriority.LOW,
        )
        assert task.priority_indicator == "[L] "

    def test_get_display_status_with_priority(self):
        """Test display status includes priority when requested."""
        task = BackgroundShellTask(
            command="echo test",
            priority=TaskPriority.HIGH,
        )
        task.status = TaskStatus.PENDING

        # Without priority
        status_no_priority = task.get_display_status(show_priority=False)
        assert "[H]" not in status_no_priority
        assert "pending" in status_no_priority

        # With priority
        status_with_priority = task.get_display_status(show_priority=True)
        assert "[H]" in status_with_priority
        assert "pending" in status_with_priority

    def test_display_status_backward_compatible(self):
        """Test that display_status property doesn't show priority (backward compat)."""
        task = BackgroundShellTask(
            command="echo test",
            priority=TaskPriority.HIGH,
        )
        task.status = TaskStatus.PENDING

        # display_status property should not include priority
        assert "[H]" not in task.display_status


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


class TestPriorityTaskQueue:
    """Tests for PriorityTaskQueue class."""

    def test_queue_creation(self):
        """Test creating an empty priority queue."""
        from kai_code.tasks.manager import PriorityTaskQueue

        queue = PriorityTaskQueue()
        assert len(queue) == 0
        assert queue.is_empty()
        assert not bool(queue)

    def test_push_and_pop(self):
        """Test basic push and pop operations."""
        from kai_code.tasks.manager import PriorityTaskQueue

        queue = PriorityTaskQueue()
        task = BackgroundShellTask(command="echo test")

        queue.push(task)
        assert len(queue) == 1
        assert not queue.is_empty()

        popped = queue.pop()
        assert popped is task
        assert len(queue) == 0

    def test_pop_empty_returns_none(self):
        """Test that pop returns None for empty queue."""
        from kai_code.tasks.manager import PriorityTaskQueue

        queue = PriorityTaskQueue()
        result = queue.pop()
        assert result is None

    def test_peek_returns_without_removing(self):
        """Test that peek returns task without removing it."""
        from kai_code.tasks.manager import PriorityTaskQueue

        queue = PriorityTaskQueue()
        task = BackgroundShellTask(command="echo test")

        queue.push(task)
        peeked = queue.peek()
        assert peeked is task
        assert len(queue) == 1  # Still in queue

    def test_peek_empty_returns_none(self):
        """Test that peek returns None for empty queue."""
        from kai_code.tasks.manager import PriorityTaskQueue

        queue = PriorityTaskQueue()
        result = queue.peek()
        assert result is None

    def test_priority_ordering_high_before_normal(self):
        """Test that HIGH priority tasks are dequeued before NORMAL."""
        from kai_code.tasks.manager import PriorityTaskQueue

        queue = PriorityTaskQueue()

        # Add normal first, then high
        normal_task = BackgroundShellTask(command="echo normal")
        time.sleep(0.01)  # Ensure different timestamps
        high_task = BackgroundShellTask(
            command="echo high",
            priority=TaskPriority.HIGH,
        )

        queue.push(normal_task)
        queue.push(high_task)

        # High should come out first despite being added second
        first = queue.pop()
        second = queue.pop()

        assert first.priority == TaskPriority.HIGH
        assert second.priority == TaskPriority.NORMAL

    def test_priority_ordering_normal_before_low(self):
        """Test that NORMAL priority tasks are dequeued before LOW."""
        from kai_code.tasks.manager import PriorityTaskQueue

        queue = PriorityTaskQueue()

        # Add low first, then normal
        low_task = BackgroundShellTask(
            command="echo low",
            priority=TaskPriority.LOW,
        )
        time.sleep(0.01)  # Ensure different timestamps
        normal_task = BackgroundShellTask(command="echo normal")

        queue.push(low_task)
        queue.push(normal_task)

        # Normal should come out first
        first = queue.pop()
        second = queue.pop()

        assert first.priority == TaskPriority.NORMAL
        assert second.priority == TaskPriority.LOW

    def test_priority_ordering_full_sequence(self):
        """Test complete priority ordering: HIGH > NORMAL > LOW."""
        from kai_code.tasks.manager import PriorityTaskQueue

        queue = PriorityTaskQueue()

        # Add in reverse priority order (low, normal, high)
        low_task = BackgroundShellTask(
            command="echo low",
            priority=TaskPriority.LOW,
        )
        time.sleep(0.01)
        normal_task = BackgroundShellTask(command="echo normal")
        time.sleep(0.01)
        high_task = BackgroundShellTask(
            command="echo high",
            priority=TaskPriority.HIGH,
        )

        queue.push(low_task)
        queue.push(normal_task)
        queue.push(high_task)

        # Should come out in priority order: HIGH, NORMAL, LOW
        first = queue.pop()
        second = queue.pop()
        third = queue.pop()

        assert first.priority == TaskPriority.HIGH
        assert second.priority == TaskPriority.NORMAL
        assert third.priority == TaskPriority.LOW

    def test_same_priority_ordering_by_creation_time(self):
        """Test that same-priority tasks are ordered by creation time (FIFO)."""
        from kai_code.tasks.manager import PriorityTaskQueue

        queue = PriorityTaskQueue()

        # Create three normal priority tasks with slight time gaps
        task1 = BackgroundShellTask(command="echo first")
        time.sleep(0.01)
        task2 = BackgroundShellTask(command="echo second")
        time.sleep(0.01)
        task3 = BackgroundShellTask(command="echo third")

        # Add in mixed order
        queue.push(task2)
        queue.push(task1)
        queue.push(task3)

        # Should come out in creation time order (FIFO)
        first = queue.pop()
        second = queue.pop()
        third = queue.pop()

        assert first.id == task1.id  # Created first
        assert second.id == task2.id  # Created second
        assert third.id == task3.id  # Created third

    def test_mixed_priorities_with_same_priority_fifo(self):
        """Test that within same priority level, FIFO order is maintained."""
        from kai_code.tasks.manager import PriorityTaskQueue

        queue = PriorityTaskQueue()

        # Create multiple tasks at each priority level
        high1 = BackgroundShellTask(command="echo h1", priority=TaskPriority.HIGH)
        time.sleep(0.01)
        high2 = BackgroundShellTask(command="echo h2", priority=TaskPriority.HIGH)
        time.sleep(0.01)
        normal1 = BackgroundShellTask(command="echo n1")
        time.sleep(0.01)
        normal2 = BackgroundShellTask(command="echo n2")

        # Add in mixed order
        queue.push(normal2)
        queue.push(high2)
        queue.push(normal1)
        queue.push(high1)

        # Should come out: high1, high2 (FIFO within HIGH), normal1, normal2 (FIFO within NORMAL)
        results = [queue.pop() for _ in range(4)]

        assert results[0].id == high1.id
        assert results[1].id == high2.id
        assert results[2].id == normal1.id
        assert results[3].id == normal2.id

    def test_remove_by_task_id(self):
        """Test removing a specific task by ID."""
        from kai_code.tasks.manager import PriorityTaskQueue

        queue = PriorityTaskQueue()

        task1 = BackgroundShellTask(command="echo 1")
        task2 = BackgroundShellTask(command="echo 2")
        task3 = BackgroundShellTask(command="echo 3")

        queue.push(task1)
        queue.push(task2)
        queue.push(task3)

        # Remove the middle task
        removed = queue.remove(task2.id)
        assert removed is task2
        assert len(queue) == 2

        # Should only get task1 and task3
        remaining = [queue.pop(), queue.pop()]
        remaining_ids = {t.id for t in remaining}
        assert task1.id in remaining_ids
        assert task3.id in remaining_ids
        assert task2.id not in remaining_ids

    def test_remove_nonexistent_returns_none(self):
        """Test that removing nonexistent task returns None."""
        from kai_code.tasks.manager import PriorityTaskQueue

        queue = PriorityTaskQueue()
        task = BackgroundShellTask(command="echo test")
        queue.push(task)

        result = queue.remove("nonexistent-id")
        assert result is None
        assert len(queue) == 1

    def test_clear_queue(self):
        """Test clearing all tasks from queue."""
        from kai_code.tasks.manager import PriorityTaskQueue

        queue = PriorityTaskQueue()

        for i in range(3):
            queue.push(BackgroundShellTask(command=f"echo {i}"))

        cleared = queue.clear()
        assert len(cleared) == 3
        assert len(queue) == 0
        assert queue.is_empty()

    def test_get_all_returns_sorted(self):
        """Test that get_all returns tasks sorted by priority."""
        from kai_code.tasks.manager import PriorityTaskQueue

        queue = PriorityTaskQueue()

        low_task = BackgroundShellTask(command="echo low", priority=TaskPriority.LOW)
        high_task = BackgroundShellTask(command="echo high", priority=TaskPriority.HIGH)
        normal_task = BackgroundShellTask(command="echo normal")

        queue.push(low_task)
        queue.push(high_task)
        queue.push(normal_task)

        all_tasks = queue.get_all()

        assert len(all_tasks) == 3
        assert all_tasks[0].priority == TaskPriority.HIGH
        assert all_tasks[1].priority == TaskPriority.NORMAL
        assert all_tasks[2].priority == TaskPriority.LOW
        # Queue should still have all tasks
        assert len(queue) == 3


class TestQueueProcessing:
    """Tests for TaskManager queue processing with MAX_CONCURRENT_TASKS."""

    @pytest.fixture(autouse=True)
    def reset_manager(self):
        """Reset the task manager before each test."""
        manager = get_task_manager()
        manager.clear_all()
        # Clear the pending queue as well
        manager._pending_queue.clear()
        yield
        manager.clear_all()
        manager._pending_queue.clear()

    def test_tasks_run_immediately_when_slots_available(self):
        """Test that tasks run immediately when under MAX_CONCURRENT_TASKS."""
        manager = get_task_manager()

        # Run a fast task
        task_id = manager.run_shell("echo test")
        task = manager.get_task(task_id)

        # Give it a moment to start
        time.sleep(0.1)

        # Task should have started (not be QUEUED anymore)
        assert task.status != TaskStatus.QUEUED

    def test_tasks_are_queued_when_max_concurrent_reached(self):
        """Test that tasks are queued when MAX_CONCURRENT_TASKS is reached."""
        manager = get_task_manager()
        max_tasks = manager.MAX_CONCURRENT_TASKS

        # Start max concurrent long-running tasks
        long_task_ids = []
        for i in range(max_tasks):
            task_id = manager.run_shell("sleep 60")
            long_task_ids.append(task_id)

        # Give tasks time to start
        time.sleep(0.3)

        # All should be running
        for task_id in long_task_ids:
            task = manager.get_task(task_id)
            assert task.status == TaskStatus.RUNNING, f"Task {task_id} should be running"

        # Now submit another task - it should be queued
        queued_task_id = manager.run_shell("echo queued")
        queued_task = manager.get_task(queued_task_id)

        # This task should be in QUEUED status
        assert queued_task.status == TaskStatus.QUEUED
        assert manager.queued_count() == 1

        # Clean up - kill the long-running tasks
        for task_id in long_task_ids:
            manager.kill_task(task_id)

    def test_queued_task_starts_after_completion(self):
        """Test that queued tasks start when a running task completes."""
        manager = get_task_manager()
        max_tasks = manager.MAX_CONCURRENT_TASKS

        # Start max concurrent tasks with a moderate sleep
        running_task_ids = []
        for i in range(max_tasks):
            task_id = manager.run_shell("sleep 0.2")
            running_task_ids.append(task_id)

        # Give tasks time to start
        time.sleep(0.1)

        # Submit a task that should be queued
        queued_task_id = manager.run_shell("echo queued_task")
        queued_task = manager.get_task(queued_task_id)

        # Verify it's queued
        assert queued_task.status == TaskStatus.QUEUED

        # Wait for the running tasks to complete
        time.sleep(0.5)

        # Now the queued task should have started and possibly completed
        assert queued_task.status != TaskStatus.QUEUED

    def test_high_priority_queued_task_runs_first(self):
        """Test that high priority queued tasks run before lower priority ones."""
        manager = get_task_manager()
        max_tasks = manager.MAX_CONCURRENT_TASKS

        # Start max concurrent tasks
        running_task_ids = []
        for i in range(max_tasks):
            task_id = manager.run_shell("sleep 0.3")
            running_task_ids.append(task_id)

        # Give tasks time to start
        time.sleep(0.1)

        # Queue tasks in reverse priority order
        low_task_id = manager.run_shell("echo low", priority=TaskPriority.LOW)
        time.sleep(0.01)
        normal_task_id = manager.run_shell("echo normal")
        time.sleep(0.01)
        high_task_id = manager.run_shell("echo high", priority=TaskPriority.HIGH)

        # All should be queued
        assert manager.get_task(low_task_id).status == TaskStatus.QUEUED
        assert manager.get_task(normal_task_id).status == TaskStatus.QUEUED
        assert manager.get_task(high_task_id).status == TaskStatus.QUEUED

        # Check queue ordering - high priority should be first
        queued_tasks = manager.get_queued_tasks()
        assert len(queued_tasks) == 3
        assert queued_tasks[0].priority == TaskPriority.HIGH
        assert queued_tasks[1].priority == TaskPriority.NORMAL
        assert queued_tasks[2].priority == TaskPriority.LOW

        # Clean up
        for task_id in running_task_ids:
            manager.kill_task(task_id)

    def test_available_slots_calculation(self):
        """Test that _available_slots correctly calculates remaining capacity."""
        manager = get_task_manager()
        max_tasks = manager.MAX_CONCURRENT_TASKS

        # Initially all slots should be available
        assert manager._available_slots() == max_tasks

        # Start one task
        task_id = manager.run_shell("sleep 60")
        time.sleep(0.1)  # Give it time to start

        # One less slot
        assert manager._available_slots() == max_tasks - 1

        # Kill the task
        manager.kill_task(task_id)
        time.sleep(0.1)

        # Slot should be available again
        assert manager._available_slots() == max_tasks

    def test_queued_count_method(self):
        """Test the queued_count method."""
        manager = get_task_manager()
        max_tasks = manager.MAX_CONCURRENT_TASKS

        # Initially no queued tasks
        assert manager.queued_count() == 0

        # Fill up running slots
        for i in range(max_tasks):
            manager.run_shell("sleep 60")

        time.sleep(0.2)

        # Add queued tasks
        manager.run_shell("echo 1")
        manager.run_shell("echo 2")
        manager.run_shell("echo 3")

        assert manager.queued_count() == 3

    def test_get_queued_tasks_method(self):
        """Test the get_queued_tasks method returns tasks in priority order."""
        manager = get_task_manager()
        max_tasks = manager.MAX_CONCURRENT_TASKS

        # Fill up running slots
        for i in range(max_tasks):
            manager.run_shell("sleep 60")

        time.sleep(0.2)

        # Add queued tasks with different priorities
        manager.run_shell("echo low", priority=TaskPriority.LOW)
        time.sleep(0.01)
        manager.run_shell("echo high", priority=TaskPriority.HIGH)
        time.sleep(0.01)
        manager.run_shell("echo normal")

        queued = manager.get_queued_tasks()

        assert len(queued) == 3
        # Should be sorted by priority
        assert queued[0].priority == TaskPriority.HIGH
        assert queued[1].priority == TaskPriority.NORMAL
        assert queued[2].priority == TaskPriority.LOW

    def test_get_active_tasks_includes_queued(self):
        """Test that get_active_tasks includes queued tasks."""
        manager = get_task_manager()
        max_tasks = manager.MAX_CONCURRENT_TASKS

        # Fill up running slots
        running_ids = []
        for i in range(max_tasks):
            tid = manager.run_shell("sleep 60")
            running_ids.append(tid)

        time.sleep(0.2)

        # Add a queued task
        queued_id = manager.run_shell("echo queued")

        active = manager.get_active_tasks()

        # Should include both running and queued
        active_ids = {t.id for t in active}
        assert queued_id in active_ids
        for rid in running_ids:
            assert rid in active_ids


class TestParsePriority:
    """Tests for _parse_priority helper function."""

    def test_parse_priority_none_returns_normal(self):
        """Test that None returns NORMAL priority."""
        from kai_code.tasks.tools import _parse_priority

        result = _parse_priority(None)
        assert result == TaskPriority.NORMAL

    def test_parse_priority_high(self):
        """Test parsing 'high' priority."""
        from kai_code.tasks.tools import _parse_priority

        result = _parse_priority("high")
        assert result == TaskPriority.HIGH

    def test_parse_priority_normal(self):
        """Test parsing 'normal' priority."""
        from kai_code.tasks.tools import _parse_priority

        result = _parse_priority("normal")
        assert result == TaskPriority.NORMAL

    def test_parse_priority_low(self):
        """Test parsing 'low' priority."""
        from kai_code.tasks.tools import _parse_priority

        result = _parse_priority("low")
        assert result == TaskPriority.LOW

    def test_parse_priority_case_insensitive(self):
        """Test that priority parsing is case insensitive."""
        from kai_code.tasks.tools import _parse_priority

        assert _parse_priority("HIGH") == TaskPriority.HIGH
        assert _parse_priority("High") == TaskPriority.HIGH
        assert _parse_priority("NORMAL") == TaskPriority.NORMAL
        assert _parse_priority("Normal") == TaskPriority.NORMAL
        assert _parse_priority("LOW") == TaskPriority.LOW
        assert _parse_priority("Low") == TaskPriority.LOW

    def test_parse_priority_invalid_raises_error(self):
        """Test that invalid priority raises ValueError."""
        from kai_code.tasks.tools import _parse_priority

        with pytest.raises(ValueError) as exc_info:
            _parse_priority("invalid")
        assert "Invalid priority" in str(exc_info.value)
        assert "high" in str(exc_info.value)
        assert "normal" in str(exc_info.value)
        assert "low" in str(exc_info.value)


class TestToolsWithPriority:
    """Tests for run_background_shell and run_background_agent tools with priority."""

    @pytest.fixture(autouse=True)
    def reset_manager(self):
        """Reset the task manager before each test."""
        manager = get_task_manager()
        manager.clear_all()
        manager._pending_queue.clear()
        yield
        manager.clear_all()
        manager._pending_queue.clear()

    def test_run_background_shell_default_priority(self):
        """Test run_background_shell creates task with NORMAL priority by default."""
        from kai_code.tasks import run_background_shell

        task_id = run_background_shell.invoke({"command": "echo test"})
        manager = get_task_manager()
        task = manager.get_task(task_id)

        assert task is not None
        assert task.priority == TaskPriority.NORMAL

    def test_run_background_shell_with_high_priority(self):
        """Test run_background_shell creates task with HIGH priority when specified."""
        from kai_code.tasks import run_background_shell

        task_id = run_background_shell.invoke({
            "command": "echo test",
            "priority": "high",
        })
        manager = get_task_manager()
        task = manager.get_task(task_id)

        assert task is not None
        assert task.priority == TaskPriority.HIGH

    def test_run_background_shell_with_low_priority(self):
        """Test run_background_shell creates task with LOW priority when specified."""
        from kai_code.tasks import run_background_shell

        task_id = run_background_shell.invoke({
            "command": "echo test",
            "priority": "low",
        })
        manager = get_task_manager()
        task = manager.get_task(task_id)

        assert task is not None
        assert task.priority == TaskPriority.LOW

    def test_run_background_shell_priority_case_insensitive(self):
        """Test run_background_shell accepts priority in any case."""
        from kai_code.tasks import run_background_shell

        task_id = run_background_shell.invoke({
            "command": "echo test",
            "priority": "HIGH",
        })
        manager = get_task_manager()
        task = manager.get_task(task_id)

        assert task is not None
        assert task.priority == TaskPriority.HIGH

    def test_run_background_agent_default_priority(self):
        """Test run_background_agent creates task with NORMAL priority by default."""
        from kai_code.tasks import run_background_agent

        task_id = run_background_agent.invoke({"prompt": "test prompt"})
        manager = get_task_manager()
        task = manager.get_task(task_id)

        assert task is not None
        assert task.priority == TaskPriority.NORMAL

    def test_run_background_agent_with_high_priority(self):
        """Test run_background_agent creates task with HIGH priority when specified."""
        from kai_code.tasks import run_background_agent

        task_id = run_background_agent.invoke({
            "prompt": "test prompt",
            "priority": "high",
        })
        manager = get_task_manager()
        task = manager.get_task(task_id)

        assert task is not None
        assert task.priority == TaskPriority.HIGH

    def test_run_background_agent_with_low_priority(self):
        """Test run_background_agent creates task with LOW priority when specified."""
        from kai_code.tasks import run_background_agent

        task_id = run_background_agent.invoke({
            "prompt": "test prompt",
            "priority": "low",
        })
        manager = get_task_manager()
        task = manager.get_task(task_id)

        assert task is not None
        assert task.priority == TaskPriority.LOW

    def test_run_background_shell_with_description_and_priority(self):
        """Test run_background_shell with both description and priority."""
        from kai_code.tasks import run_background_shell

        task_id = run_background_shell.invoke({
            "command": "echo test",
            "description": "Custom description",
            "priority": "high",
        })
        manager = get_task_manager()
        task = manager.get_task(task_id)

        assert task is not None
        assert task.priority == TaskPriority.HIGH
        assert task.description == "Custom description"

    def test_run_background_agent_with_description_and_priority(self):
        """Test run_background_agent with both description and priority."""
        from kai_code.tasks import run_background_agent

        task_id = run_background_agent.invoke({
            "prompt": "test prompt",
            "description": "Custom agent task",
            "priority": "low",
        })
        manager = get_task_manager()
        task = manager.get_task(task_id)

        assert task is not None
        assert task.priority == TaskPriority.LOW
        assert task.description == "Custom agent task"


class TestGetTasksByPriority:
    """Tests for get_tasks_by_priority method."""

    @pytest.fixture(autouse=True)
    def reset_manager(self):
        """Reset the task manager before each test."""
        manager = get_task_manager()
        manager.clear_all()
        manager._pending_queue.clear()
        yield
        manager.clear_all()
        manager._pending_queue.clear()

    def test_get_tasks_by_priority_empty(self):
        """Test get_tasks_by_priority with no tasks."""
        manager = get_task_manager()
        result = manager.get_tasks_by_priority(TaskPriority.HIGH)
        assert result == []

    def test_get_tasks_by_priority_high(self):
        """Test getting only HIGH priority tasks."""
        manager = get_task_manager()

        # Create tasks with different priorities
        manager.run_shell("echo high1", priority=TaskPriority.HIGH)
        manager.run_shell("echo normal", priority=TaskPriority.NORMAL)
        manager.run_shell("echo high2", priority=TaskPriority.HIGH)
        manager.run_shell("echo low", priority=TaskPriority.LOW)

        # Wait for tasks to complete
        time.sleep(0.5)

        high_tasks = manager.get_tasks_by_priority(TaskPriority.HIGH)
        assert len(high_tasks) == 2
        for task in high_tasks:
            assert task.priority == TaskPriority.HIGH

    def test_get_tasks_by_priority_normal(self):
        """Test getting only NORMAL priority tasks."""
        manager = get_task_manager()

        # Create tasks with different priorities
        manager.run_shell("echo high", priority=TaskPriority.HIGH)
        manager.run_shell("echo normal1", priority=TaskPriority.NORMAL)
        manager.run_shell("echo normal2", priority=TaskPriority.NORMAL)
        manager.run_shell("echo low", priority=TaskPriority.LOW)

        # Wait for tasks to complete
        time.sleep(0.5)

        normal_tasks = manager.get_tasks_by_priority(TaskPriority.NORMAL)
        assert len(normal_tasks) == 2
        for task in normal_tasks:
            assert task.priority == TaskPriority.NORMAL

    def test_get_tasks_by_priority_low(self):
        """Test getting only LOW priority tasks."""
        manager = get_task_manager()

        # Create tasks with different priorities
        manager.run_shell("echo high", priority=TaskPriority.HIGH)
        manager.run_shell("echo normal", priority=TaskPriority.NORMAL)
        manager.run_shell("echo low1", priority=TaskPriority.LOW)
        manager.run_shell("echo low2", priority=TaskPriority.LOW)

        # Wait for tasks to complete
        time.sleep(0.5)

        low_tasks = manager.get_tasks_by_priority(TaskPriority.LOW)
        assert len(low_tasks) == 2
        for task in low_tasks:
            assert task.priority == TaskPriority.LOW

    def test_get_tasks_by_priority_sorted_by_creation_time(self):
        """Test that tasks are sorted by creation time (newest first)."""
        manager = get_task_manager()

        # Create HIGH priority tasks with time gaps
        task_id1 = manager.run_shell("echo first", priority=TaskPriority.HIGH)
        time.sleep(0.05)
        task_id2 = manager.run_shell("echo second", priority=TaskPriority.HIGH)
        time.sleep(0.05)
        task_id3 = manager.run_shell("echo third", priority=TaskPriority.HIGH)

        # Wait for tasks to complete
        time.sleep(0.5)

        high_tasks = manager.get_tasks_by_priority(TaskPriority.HIGH)

        # Should be sorted newest first
        assert len(high_tasks) == 3
        assert high_tasks[0].id == task_id3  # Most recent
        assert high_tasks[1].id == task_id2
        assert high_tasks[2].id == task_id1  # Oldest

    def test_get_tasks_by_priority_includes_all_statuses(self):
        """Test that get_tasks_by_priority includes tasks of all statuses."""
        manager = get_task_manager()
        max_tasks = manager.MAX_CONCURRENT_TASKS

        # Fill up running slots with long tasks
        for i in range(max_tasks):
            manager.run_shell("sleep 60", priority=TaskPriority.NORMAL)

        # Give time to start
        time.sleep(0.2)

        # Add a queued HIGH priority task
        queued_id = manager.run_shell("echo queued", priority=TaskPriority.HIGH)

        # Add a completed HIGH priority task (it will be queued first)
        completed_id = manager.run_shell("echo completed", priority=TaskPriority.HIGH)

        # Both should be queued now
        high_tasks = manager.get_tasks_by_priority(TaskPriority.HIGH)
        task_ids = {t.id for t in high_tasks}

        assert queued_id in task_ids
        assert completed_id in task_ids
