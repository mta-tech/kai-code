"""Hybrid async/thread task manager for background execution.

Uses asyncio for I/O-bound shell tasks and ThreadPoolExecutor for CPU-bound
agent tasks, providing optimal performance for each workload type.
"""
from __future__ import annotations

import asyncio
import io
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Callable


class TaskStatus(Enum):
    """Status of a background task."""
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    KILLED = "killed"
    TIMED_OUT = "timed_out"


@dataclass
class Task:
    """Simple task record with serialization safety."""

    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    status: TaskStatus = TaskStatus.QUEUED
    command: str = ""
    output: str = ""
    error: str | None = None
    created_at: datetime = field(default_factory=datetime.now)
    started_at: datetime | None = None
    finished_at: datetime | None = None
    exit_code: int | None = None
    type: str = "shell"  # "shell" or "agent"

    # Runtime-only state (excluded from serialization)
    _asyncio_task: asyncio.Task | None = field(default=None, repr=False, compare=False)

    def __getstate__(self) -> dict:
        """Exclude runtime-only state from serialization."""
        state = self.__dict__.copy()
        state.pop('_asyncio_task', None)
        return state

    def __setstate__(self, state: dict) -> None:
        """Restore serialized state and recreate runtime objects."""
        self.__dict__.update(state)
        self._asyncio_task = None

    @property
    def duration(self) -> float | None:
        """Get task duration in seconds."""
        if self.finished_at and self.started_at:
            return (self.finished_at - self.started_at).total_seconds()
        if self.status == TaskStatus.RUNNING and self.started_at:
            return (datetime.now() - self.started_at).total_seconds()
        return None


class HybridTaskManager:
    """Hybrid task manager using asyncio for I/O and threads for CPU.

    Shell tasks use asyncio subprocess for non-blocking I/O.
    Agent tasks use ThreadPoolExecutor for CPU-bound execution.
    """

    DEFAULT_TIMEOUT: int = 900  # 15 minutes
    MAX_SHELL_TASKS: int = 20   # High concurrency for I/O-bound
    MAX_AGENT_TASKS: int = 2    # Low concurrency for CPU-bound

    def __init__(self) -> None:
        self._tasks: dict[str, Task] = {}
        self._shell_semaphore = asyncio.Semaphore(self.MAX_SHELL_TASKS)
        self._agent_executor = ThreadPoolExecutor(max_workers=self.MAX_AGENT_TASKS)
        self._callbacks: list[Callable[[Task], None]] = []
        self._tracked_tasks: set[asyncio.Task] = set()
        self._root_dir = Path.cwd()
        self._model = "default"

    def configure(self, root_dir: Path | None = None, model: str | None = None) -> None:
        """Configure default settings for new tasks."""
        if root_dir is not None:
            self._root_dir = root_dir
        if model is not None:
            self._model = model

    async def run_shell(
        self,
        command: str,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> str:
        """Run shell command asynchronously with timeout.

        Args:
            command: Shell command to execute
            timeout: Maximum execution time in seconds

        Returns:
            Task ID
        """
        task = Task(id=str(uuid.uuid4())[:8], command=command, type="shell")
        self._tasks[task.id] = task

        # Create and track background task
        async_task = asyncio.create_task(self._run_shell_task(task, timeout))
        self._tracked_tasks.add(async_task)
        async_task.add_done_callback(self._tracked_tasks.discard)

        return task.id

    async def _run_shell_task(self, task: Task, timeout: int) -> None:
        """Execute shell task with timeout."""
        async with self._shell_semaphore:
            task.status = TaskStatus.RUNNING
            task.started_at = datetime.now()

            proc = None
            try:
                # Use create_subprocess_exec (NOT shell) for security
                proc = await asyncio.create_subprocess_exec(
                    "bash", "-c", task.command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.STDOUT,
                )

                # Use StringIO for O(n) string building (not O(n²))
                buffer = io.StringIO()

                async with asyncio.timeout(timeout):
                    while True:
                        if proc is None or proc.stdout is None:
                            break
                        line = await proc.stdout.readline()
                        if not line:
                            break
                        buffer.write(line.decode('utf-8', errors='replace'))

                task.output = buffer.getvalue()
                if proc is not None:
                    task.exit_code = await proc.wait()
                task.status = TaskStatus.COMPLETED

            except asyncio.TimeoutError:
                if proc:
                    proc.kill()
                    await proc.wait()
                task.status = TaskStatus.TIMED_OUT
                task.error = f"Timeout after {timeout}s"

            except Exception as e:
                task.status = TaskStatus.FAILED
                task.error = str(e)

            finally:
                task.finished_at = datetime.now()
                self._notify_completion(task)

    async def run_agent(
        self,
        prompt: str,
        root_dir: Path | None = None,
        model: str | None = None,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> str:
        """Run agent in thread pool (CPU-bound).

        Args:
            prompt: Prompt to send to the agent
            root_dir: Root directory for the agent
            model: Model to use
            timeout: Maximum execution time in seconds

        Returns:
            Task ID
        """
        task = Task(
            id=str(uuid.uuid4())[:8],
            command=f"[agent] {prompt[:50]}",
            type="agent",
        )
        self._tasks[task.id] = task

        # Run in thread pool with timeout
        loop = asyncio.get_running_loop()

        async def run_agent_with_timeout() -> None:
            await asyncio.wait_for(
                loop.run_in_executor(
                    self._agent_executor,
                    self._run_agent_sync,
                    prompt,
                    root_dir or self._root_dir,
                    model or self._model,
                    task,
                ),
                timeout=timeout,
            )

        # Track completion
        async def track_completion() -> None:
            try:
                await run_agent_with_timeout()
            except asyncio.TimeoutError:
                task.status = TaskStatus.TIMED_OUT
                task.error = f"Timeout after {timeout}s"
                task.finished_at = datetime.now()
            finally:
                self._notify_completion(task)

        tracked = asyncio.create_task(track_completion())
        self._tracked_tasks.add(tracked)
        tracked.add_done_callback(self._tracked_tasks.discard)

        return task.id

    def _run_agent_sync(
        self,
        prompt: str,
        root_dir: Path,
        model: str,
        task: Task,
    ) -> None:
        """Synchronous agent execution (runs in thread pool)."""
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now()

        try:
            from ..agent import KaiAgent

            agent = KaiAgent(root_dir=root_dir, model=model, yolo=True)
            result = agent.run(prompt)
            task.output = result.output
            task.status = TaskStatus.COMPLETED

        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = str(e)

        finally:
            task.finished_at = datetime.now()

    async def kill(self, task_id: str) -> bool:
        """Cancel a running task."""
        task = self._tasks.get(task_id)
        if not task or task.status != TaskStatus.RUNNING:
            return False

        task.status = TaskStatus.KILLED
        task.finished_at = datetime.now()
        return True

    async def kill_all(self) -> int:
        """Kill all running tasks. Returns count of killed tasks."""
        count = 0
        for task in self._tasks.values():
            if task.status == TaskStatus.RUNNING:
                await self.kill(task.id)
                count += 1
        return count

    def get_task(self, task_id: str) -> Task | None:
        """Get task by ID."""
        return self._tasks.get(task_id)

    def get_all_tasks(self) -> list[Task]:
        """Get all tasks, sorted by creation time (newest first)."""
        return sorted(
            self._tasks.values(),
            key=lambda t: t.created_at,
            reverse=True,
        )

    def get_active_tasks(self) -> list[Task]:
        """Get all running or queued tasks."""
        return [
            t for t in self._tasks.values()
            if t.status in (TaskStatus.QUEUED, TaskStatus.RUNNING)
        ]

    def active_count(self) -> int:
        """Get count of active tasks."""
        return len(self.get_active_tasks())

    def total_count(self) -> int:
        """Get total task count."""
        return len(self._tasks)

    async def clear_completed(self) -> int:
        """Remove all completed tasks. Returns count of cleared tasks."""
        completed_ids = [
            t.id for t in self._tasks.values()
            if t.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.KILLED, TaskStatus.TIMED_OUT)
        ]
        for task_id in completed_ids:
            del self._tasks[task_id]
        return len(completed_ids)

    async def clear_all(self) -> None:
        """Kill all tasks and clear the list."""
        await self.kill_all()
        self._tasks.clear()

    def on_task_complete(self, callback: Callable[[Task], None]) -> None:
        """Register a callback for task completion."""
        self._callbacks.append(callback)

    def _notify_completion(self, task: Task) -> None:
        """Notify callbacks when a task completes."""
        for callback in self._callbacks:
            try:
                callback(task)
            except Exception:
                pass

    async def shutdown(self, timeout: float = 5.0) -> None:
        """Shutdown gracefully.

        Args:
            timeout: Maximum time to wait for tasks to complete
        """
        # Cancel all async tasks
        for async_task in self._tracked_tasks:
            async_task.cancel()

        # Wait for cancellation with timeout
        if self._tracked_tasks:
            try:
                await asyncio.wait(self._tracked_tasks, timeout=timeout)
            except asyncio.TimeoutError:
                pass

        # Mark all running tasks as killed
        for task in self._tasks.values():
            if task.status == TaskStatus.RUNNING:
                task.status = TaskStatus.KILLED
                task.finished_at = datetime.now()

        # Shutdown thread pool (timeout parameter not available in Python <3.9)
        self._agent_executor.shutdown(wait=True)

        # Clean up
        self._tracked_tasks.clear()


# Global singleton instance
_hybrid_task_manager: HybridTaskManager | None = None


def get_hybrid_task_manager() -> HybridTaskManager:
    """Get the global HybridTaskManager instance."""
    global _hybrid_task_manager
    if _hybrid_task_manager is None:
        _hybrid_task_manager = HybridTaskManager()

        # TODO: Register completion callback for auto-nudge
        # The TaskCompletionNotifier expects the old Task type from task.py
        # We need to create an adapter to bridge the types during Phase 3
        # from .notifier import TaskCompletionNotifier
        # from .registry import get_agent_task_registry
        # from .active_agents import get_active_agent_registry
        # notifier = TaskCompletionNotifier(
        #     get_agent_task_registry(),
        #     get_active_agent_registry(),
        # )
        # _hybrid_task_manager.on_task_complete(notifier)

    return _hybrid_task_manager
