"""Background task management for kai-code.

This module provides background execution of shell commands and agent tasks,
with support for task priorities and a priority queue system.

Usage:
    from kai_code.tasks import get_task_manager, TaskStatus, TaskPriority

    # Get the singleton manager
    manager = get_task_manager()

    # Run a shell command in background
    task_id = manager.run_shell("pytest tests/ -v")

    # Run an agent prompt in background
    task_id = manager.run_agent("Review the auth module")

    # Run tasks with priority
    # HIGH priority tasks execute before NORMAL, which execute before LOW
    task_id = manager.run_shell("urgent-fix.sh", priority=TaskPriority.HIGH)
    task_id = manager.run_agent("Review code", priority=TaskPriority.LOW)

    # Check task status
    task = manager.get_task(task_id)
    if task.status == TaskStatus.COMPLETED:
        print(task.output)

    # Check for queued tasks (waiting for execution slots)
    if task.status == TaskStatus.QUEUED:
        print(f"Task {task.id} is waiting in queue")

    # List all tasks
    for task in manager.get_all_tasks():
        print(f"{task.description}: {task.display_status}")

    # Query tasks by priority
    high_priority = manager.get_tasks_by_priority(TaskPriority.HIGH)
    queued = manager.get_queued_tasks()
    print(f"Queued tasks: {manager.queued_count()}")

    # Kill a running task
    manager.kill_task(task_id)

    # Clean up on exit
    manager.kill_all()
"""

from .task import (
    Task,
    TaskStatus,
    TaskPriority,
    BackgroundShellTask,
    BackgroundAgentTask,
)
from .manager import (
    TaskManager,
    get_task_manager,
)
from .panel import (
    show_tasks_panel,
    format_task_status_line,
    format_tasks_summary,
)
from .tools import (
    list_background_tasks,
    get_task_output,
    kill_background_task,
    run_background_shell,
    run_background_agent,
    _parse_priority,
    BACKGROUND_TASK_TOOLS,
)

__all__ = [
    "Task",
    "TaskStatus",
    "TaskPriority",
    "BackgroundShellTask",
    "BackgroundAgentTask",
    "TaskManager",
    "get_task_manager",
    "show_tasks_panel",
    "format_task_status_line",
    "format_tasks_summary",
    "list_background_tasks",
    "get_task_output",
    "kill_background_task",
    "run_background_shell",
    "run_background_agent",
    "_parse_priority",
    "BACKGROUND_TASK_TOOLS",
]
