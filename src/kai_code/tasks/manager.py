"""Task manager for background execution."""
from __future__ import annotations

import heapq
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Callable

from .task import (
    Task,
    TaskStatus,
    TaskPriority,
    BackgroundShellTask,
    BackgroundAgentTask,
)


class PriorityTaskQueue:
    """Thread-safe priority queue for tasks.

    Uses a heap-based priority queue with tuples of:
    (priority_value, creation_time, task_id, task)

    This ensures:
    - Tasks with lower priority values (higher priority) are dequeued first
    - Tasks with same priority are ordered by creation time (FIFO)
    - task_id provides a tiebreaker for identical timestamps
    """

    def __init__(self) -> None:
        self._heap: list[tuple[int, float, str, Task]] = []
        self._lock = threading.Lock()

    def push(self, task: Task) -> None:
        """Add a task to the queue.

        Args:
            task: The task to add. Uses task.priority and task.created_at for ordering.
        """
        with self._lock:
            # Create heap entry: (priority_value, timestamp, task_id, task)
            # Lower priority value = higher priority (dequeued first)
            # Earlier timestamp = higher priority for same priority level
            entry = (
                task.priority.value,
                task.created_at.timestamp(),
                task.id,
                task,
            )
            heapq.heappush(self._heap, entry)

    def pop(self) -> Task | None:
        """Remove and return the highest-priority task.

        Returns:
            The highest-priority task, or None if the queue is empty.
        """
        with self._lock:
            if not self._heap:
                return None
            _, _, _, task = heapq.heappop(self._heap)
            return task

    def peek(self) -> Task | None:
        """Return the highest-priority task without removing it.

        Returns:
            The highest-priority task, or None if the queue is empty.
        """
        with self._lock:
            if not self._heap:
                return None
            _, _, _, task = self._heap[0]
            return task

    def remove(self, task_id: str) -> Task | None:
        """Remove a specific task from the queue by ID.

        Args:
            task_id: The ID of the task to remove.

        Returns:
            The removed task, or None if not found.
        """
        with self._lock:
            for i, (_, _, tid, task) in enumerate(self._heap):
                if tid == task_id:
                    # Remove the item and re-heapify
                    removed_task = task
                    self._heap.pop(i)
                    heapq.heapify(self._heap)
                    return removed_task
            return None

    def clear(self) -> list[Task]:
        """Remove and return all tasks from the queue.

        Returns:
            List of all tasks that were in the queue.
        """
        with self._lock:
            tasks = [task for _, _, _, task in self._heap]
            self._heap.clear()
            return tasks

    def get_all(self) -> list[Task]:
        """Get all tasks in the queue without removing them.

        Returns:
            List of all tasks, sorted by priority (highest first).
        """
        with self._lock:
            # Return tasks sorted by their priority order
            sorted_entries = sorted(self._heap)
            return [task for _, _, _, task in sorted_entries]

    def __len__(self) -> int:
        """Return the number of tasks in the queue."""
        with self._lock:
            return len(self._heap)

    def __bool__(self) -> bool:
        """Return True if the queue is not empty."""
        with self._lock:
            return bool(self._heap)

    def is_empty(self) -> bool:
        """Check if the queue is empty.

        Returns:
            True if the queue is empty, False otherwise.
        """
        with self._lock:
            return len(self._heap) == 0


class TaskManager:
    """Singleton manager for background tasks."""

    _instance: TaskManager | None = None
    _lock = threading.Lock()

    MAX_CONCURRENT_TASKS = 5

    def __new__(cls) -> TaskManager:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        self._tasks: dict[str, Task] = {}
        self._pending_queue: PriorityTaskQueue = PriorityTaskQueue()
        self._executor = ThreadPoolExecutor(max_workers=self.MAX_CONCURRENT_TASKS)
        self._callbacks: list[Callable[[Task], None]] = []
        self._root_dir = Path.cwd()
        self._model = "default"

    def configure(self, root_dir: Path | None = None, model: str | None = None) -> None:
        """Configure default settings for new tasks."""
        if root_dir is not None:
            self._root_dir = root_dir
        if model is not None:
            self._model = model

    def run_shell(
        self,
        command: str,
        working_dir: Path | None = None,
        priority: TaskPriority = TaskPriority.NORMAL,
    ) -> str:
        """Run a shell command in the background.

        Args:
            command: Shell command to execute
            working_dir: Working directory (defaults to root_dir)
            priority: Task priority level (defaults to NORMAL)

        Returns:
            Task ID
        """
        task = BackgroundShellTask(
            command=command,
            working_dir=working_dir or self._root_dir,
            priority=priority,
        )
        return self._submit_task(task)

    def run_agent(
        self,
        prompt: str,
        root_dir: Path | None = None,
        model: str | None = None,
        priority: TaskPriority = TaskPriority.NORMAL,
    ) -> str:
        """Run an agent prompt in the background.

        Args:
            prompt: Prompt to send to the agent
            root_dir: Root directory for the agent
            model: Model to use
            priority: Task priority level (defaults to NORMAL)

        Returns:
            Task ID
        """
        task = BackgroundAgentTask(
            prompt=prompt,
            root_dir=root_dir or self._root_dir,
            model=model or self._model,
            priority=priority,
        )
        return self._submit_task(task)

    def _submit_task(self, task: Task) -> str:
        """Submit a task for background execution.

        Tasks are added to a priority queue with QUEUED status. The queue
        is then processed to start tasks if slots are available, respecting
        task priorities (high priority tasks start before lower priority ones).

        Args:
            task: The task to submit for execution.

        Returns:
            The task ID.
        """
        # Register the task
        self._tasks[task.id] = task

        # Set status to QUEUED and add to priority queue
        task.status = TaskStatus.QUEUED
        self._pending_queue.push(task)

        # Process queue to start tasks if slots are available
        self._process_queue()

        return task.id

    def _available_slots(self) -> int:
        """Return the number of available slots for running tasks.

        Calculates available capacity by subtracting currently running tasks
        from MAX_CONCURRENT_TASKS limit.

        Returns:
            Number of available slots for new tasks.
        """
        running_count = sum(
            1 for task in self._tasks.values()
            if task.status == TaskStatus.RUNNING
        )
        return max(0, self.MAX_CONCURRENT_TASKS - running_count)

    def _process_queue(self) -> None:
        """Process the pending queue and start tasks when slots are available.

        Dequeues highest-priority tasks from the pending queue and starts them
        until no more slots are available or the queue is empty.
        """
        while self._available_slots() > 0 and self._pending_queue:
            task = self._pending_queue.pop()
            if task is None:
                break

            # Start the task
            def run_and_notify(t: Task = task):
                try:
                    t.run()
                finally:
                    self._notify_completion(t)

            task._thread = threading.Thread(target=run_and_notify, daemon=True)
            task._thread.start()

    def _notify_completion(self, task: Task) -> None:
        """Notify callbacks when a task completes and process the queue.

        When a task completes, we notify all registered callbacks and then
        process the pending queue to start the next highest-priority queued
        task if slots are available.
        """
        for callback in self._callbacks:
            try:
                callback(task)
            except Exception:
                pass

        # Process queue to start next queued task if slots are available
        self._process_queue()

    def on_task_complete(self, callback: Callable[[Task], None]) -> None:
        """Register a callback for task completion."""
        self._callbacks.append(callback)

    def get_task(self, task_id: str) -> Task | None:
        """Get a task by ID."""
        return self._tasks.get(task_id)

    def get_all_tasks(self) -> list[Task]:
        """Get all tasks, sorted by creation time (newest first)."""
        return sorted(self._tasks.values(), key=lambda t: t.created_at, reverse=True)

    def get_active_tasks(self) -> list[Task]:
        """Get all running, pending, or queued tasks."""
        return [
            t for t in self._tasks.values()
            if t.status in (TaskStatus.PENDING, TaskStatus.RUNNING, TaskStatus.QUEUED)
        ]

    def get_queued_tasks(self) -> list[Task]:
        """Get all tasks waiting in the priority queue.

        Returns:
            List of queued tasks, sorted by priority (highest priority first).
        """
        return self._pending_queue.get_all()

    def get_tasks_by_priority(self, priority: TaskPriority) -> list[Task]:
        """Get all tasks with a specific priority level.

        Args:
            priority: The priority level to filter by.

        Returns:
            List of tasks with the specified priority, sorted by creation time (newest first).
        """
        return sorted(
            [t for t in self._tasks.values() if t.priority == priority],
            key=lambda t: t.created_at,
            reverse=True,
        )

    def queued_count(self) -> int:
        """Get count of tasks waiting in the queue.

        Returns:
            Number of tasks in the pending queue.
        """
        return len(self._pending_queue)

    def get_completed_tasks(self) -> list[Task]:
        """Get all completed, failed, or killed tasks."""
        return [
            t for t in self._tasks.values()
            if t.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.KILLED)
        ]

    def active_count(self) -> int:
        """Get count of active tasks."""
        return len(self.get_active_tasks())

    def total_count(self) -> int:
        """Get total task count."""
        return len(self._tasks)

    def kill_task(self, task_id: str) -> bool:
        """Kill a running task."""
        task = self._tasks.get(task_id)
        if task is None:
            return False
        return task.kill()

    def kill_all(self) -> int:
        """Kill all running tasks. Returns count of killed tasks."""
        count = 0
        for task in self.get_active_tasks():
            if task.kill():
                count += 1
        return count

    def clear_completed(self) -> int:
        """Remove all completed tasks. Returns count of cleared tasks."""
        completed_ids = [
            t.id for t in self._tasks.values()
            if t.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.KILLED)
        ]
        for task_id in completed_ids:
            del self._tasks[task_id]
        return len(completed_ids)

    def clear_all(self) -> None:
        """Kill all tasks and clear the list."""
        self.kill_all()
        self._tasks.clear()

    def shutdown(self) -> None:
        """Shutdown the task manager."""
        self.kill_all()
        self._executor.shutdown(wait=False)


# Global singleton instance
_task_manager: TaskManager | None = None


def get_task_manager() -> TaskManager:
    """Get the global TaskManager instance."""
    global _task_manager
    if _task_manager is None:
        _task_manager = TaskManager()
    return _task_manager
