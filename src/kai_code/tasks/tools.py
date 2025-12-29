"""Agent tools for interacting with background tasks."""
from __future__ import annotations

from typing import Annotated

from langchain_core.tools import tool

from .manager import get_task_manager
from .task import TaskStatus, TaskPriority


def _parse_priority(priority_str: str | None) -> TaskPriority:
    """Parse a priority string to TaskPriority enum.

    Args:
        priority_str: Priority string ('high', 'normal', 'low') or None.

    Returns:
        TaskPriority enum value.

    Raises:
        ValueError: If priority_str is not a valid priority value.
    """
    if priority_str is None:
        return TaskPriority.NORMAL

    mapping = {
        "high": TaskPriority.HIGH,
        "normal": TaskPriority.NORMAL,
        "low": TaskPriority.LOW,
    }
    priority_lower = priority_str.lower()
    if priority_lower not in mapping:
        valid = ", ".join(mapping.keys())
        raise ValueError(f"Invalid priority '{priority_str}'. Must be one of: {valid}")
    return mapping[priority_lower]


@tool
def list_background_tasks() -> str:
    """List all background tasks with their status, priority, and summary.

    Use this to see what background tasks are running, queued, completed, or failed.
    Returns a formatted list of all tasks with their IDs, types, priorities, descriptions, and status.
    """
    manager = get_task_manager()
    tasks = manager.get_all_tasks()

    if not tasks:
        return "No background tasks."

    lines = []
    active = manager.get_active_tasks()
    completed = manager.get_completed_tasks()
    queued = manager.queued_count()

    # Build summary with queued count if any
    summary_parts = [f"{len(active)} active"]
    if queued > 0:
        summary_parts.append(f"{queued} queued")
    summary_parts.append(f"{len(completed)} completed")
    lines.append(f"Background Tasks: {', '.join(summary_parts)}")
    lines.append("")

    # Format as table with priority column
    lines.append("ID       | Type   | Priority | Status    | Description")
    lines.append("-" * 70)

    for task in tasks:
        status_str = {
            TaskStatus.RUNNING: "running",
            TaskStatus.COMPLETED: "done",
            TaskStatus.FAILED: "failed",
            TaskStatus.KILLED: "killed",
            TaskStatus.PENDING: "pending",
            TaskStatus.QUEUED: "queued",
        }.get(task.status, "?")

        priority_str = {
            TaskPriority.HIGH: "high",
            TaskPriority.NORMAL: "normal",
            TaskPriority.LOW: "low",
        }.get(task.priority, "normal")

        # Truncate description
        desc = task.description
        if len(desc) > 25:
            desc = desc[:22] + "..."

        lines.append(f"{task.id:<8} | {task.type:<6} | {priority_str:<8} | {status_str:<9} | {desc}")

    return "\n".join(lines)


@tool
def get_task_output(task_id: Annotated[str, "The ID of the task to get output from"]) -> str:
    """Get the full output of a background task.

    Use this to see the complete output from a completed, failed, or running task.
    The task_id can be found using list_background_tasks.

    Args:
        task_id: The ID of the task (e.g., "a1b2c3d4")

    Returns:
        The task's output, or an error message if the task was not found.
    """
    manager = get_task_manager()
    task = manager.get_task(task_id)

    if task is None:
        return f"Task not found: {task_id}"

    lines = []
    lines.append(f"Task: {task.description}")
    lines.append(f"Type: {task.type}")
    lines.append(f"Status: {task.status.value}")

    if task.duration:
        lines.append(f"Duration: {task.duration:.1f}s")

    if task.error:
        lines.append(f"Error: {task.error}")

    lines.append("")
    lines.append("Output:")
    lines.append("-" * 40)

    if task.output:
        # Limit output size to prevent overwhelming the context
        output = task.output
        if len(output) > 10000:
            output = output[:10000] + "\n\n... (output truncated, {len(task.output) - 10000} more characters)"
        lines.append(output)
    else:
        lines.append("(no output)")

    return "\n".join(lines)


@tool
def kill_background_task(task_id: Annotated[str, "The ID of the task to kill"]) -> str:
    """Kill a running background task.

    Use this to stop a background task that is currently running.
    The task_id can be found using list_background_tasks.

    Args:
        task_id: The ID of the task to kill (e.g., "a1b2c3d4")

    Returns:
        Success or error message.
    """
    manager = get_task_manager()
    task = manager.get_task(task_id)

    if task is None:
        return f"Task not found: {task_id}"

    if task.status != TaskStatus.RUNNING:
        return f"Task is not running (status: {task.status.value})"

    success = manager.kill_task(task_id)

    if success:
        return f"Task {task_id} killed successfully."
    else:
        return f"Failed to kill task {task_id}."


@tool
def run_background_shell(
    command: Annotated[str, "The shell command to run in the background"],
    description: Annotated[str | None, "Optional description of the task"] = None,
    priority: Annotated[str | None, "Task priority: 'high', 'normal', or 'low'"] = None,
) -> str:
    """Run a shell command in the background.

    Use this for long-running commands like builds, tests, or servers.
    The task will be managed by the background task manager.

    Args:
        command: The shell command to execute.
        description: Optional description for the task.
        priority: Task priority ('high', 'normal', 'low'). Defaults to 'normal'.

    Returns:
        The task ID.
    """
    manager = get_task_manager()
    task_priority = _parse_priority(priority)
    task_id = manager.run_shell(command, priority=task_priority)
    if description:
        task = manager.get_task(task_id)
        if task:
            task.description = description
    return task_id


@tool
def run_background_agent(
    prompt: Annotated[str, "The prompt to send to the background agent"],
    description: Annotated[str | None, "Optional description of the task"] = None,
    priority: Annotated[str | None, "Task priority: 'high', 'normal', or 'low'"] = None,
) -> str:
    """Run an agent task in the background.

    Use this for complex, multi-step tasks that can run independently.
    The task will be managed by the background task manager.

    Args:
        prompt: The prompt for the agent.
        description: Optional description for the task.
        priority: Task priority ('high', 'normal', 'low'). Defaults to 'normal'.

    Returns:
        The task ID.
    """
    manager = get_task_manager()
    task_priority = _parse_priority(priority)
    task_id = manager.run_agent(prompt, priority=task_priority)
    if description:
        task = manager.get_task(task_id)
        if task:
            task.description = description
    return task_id


# Export all tools as a list for easy registration
BACKGROUND_TASK_TOOLS = [
    list_background_tasks,
    get_task_output,
    kill_background_task,
    run_background_shell,
    run_background_agent,
]
