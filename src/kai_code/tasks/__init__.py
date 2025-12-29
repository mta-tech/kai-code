"""Background task management for kai-code.

This module provides background execution of shell commands and agent tasks.

Usage:
    from kai_code.tasks import get_task_manager, TaskStatus

    # Get the singleton manager
    manager = get_task_manager()

    # Run a shell command in background
    task_id = manager.run_shell("pytest tests/ -v")

    # Run an agent prompt in background
    task_id = manager.run_agent("Review the auth module")

    # Check task status
    task = manager.get_task(task_id)
    if task.status == TaskStatus.COMPLETED:
        print(task.output)

    # List all tasks
    for task in manager.get_all_tasks():
        print(f"{task.description}: {task.display_status}")

    # Kill a running task
    manager.kill_task(task_id)

    # Clean up on exit
    manager.kill_all()
"""

from .task import (
    Task,
    TaskStatus,
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
    BACKGROUND_TASK_TOOLS,
)

__all__ = [
    "Task",
    "TaskStatus",
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
    "BACKGROUND_TASK_TOOLS",
]
