"""Agent tools for interacting with the hybrid async/thread task manager."""
from __future__ import annotations

import asyncio
from typing import Annotated

from langchain_core.tools import tool

from .hybrid_manager import get_hybrid_task_manager


def _run_async(coro):
    """Run an async coroutine from sync code.

    Args:
        coro: The coroutine to run

    Returns:
        The result of the coroutine
    """
    try:
        loop = asyncio.get_running_loop()
        # If we're already in an async context, we can't use asyncio.run()
        # This shouldn't happen with LangChain tools, but handle it gracefully
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            future = pool.submit(asyncio.run, coro)
            return future.result()
    except RuntimeError:
        # No running event loop, use asyncio.run()
        return asyncio.run(coro)


@tool
def list_hybrid_tasks() -> str:
    """List all background tasks with their status.

    Use this to see what background tasks are running, queued, completed, or failed.
    Returns a formatted list of all tasks with their IDs, types, status, and command.
    """
    manager = get_hybrid_task_manager()
    tasks = manager.get_all_tasks()

    if not tasks:
        return "No background tasks."

    lines = []
    active = manager.active_count()
    completed_count = manager.total_count() - active

    # Build summary
    lines.append(f"Background Tasks: {active} active, {completed_count} completed")
    lines.append("")

    # Format as table
    lines.append("ID       | Type   | Status    | Command")
    lines.append("-" * 70)

    for task in tasks:
        status_str = task.status.value

        # Truncate command
        cmd = task.command
        if len(cmd) > 30:
            cmd = cmd[:27] + "..."

        lines.append(f"{task.id:<8} | {task.type:<6} | {status_str:<9} | {cmd}")

    return "\n".join(lines)


@tool
def get_hybrid_task_output(
    task_id: Annotated[str, "The ID of the task to get output from"],
) -> str:
    """Get the full output of a background task.

    Args:
        task_id: The ID of the task

    Returns:
        The task output or error message
    """
    manager = get_hybrid_task_manager()
    task = manager.get_task(task_id)

    if task is None:
        return f"Task '{task_id}' not found."

    if task.status.value in ("queued", "running"):
        return (
            f"Task '{task_id}' is still {task.status.value}.\n"
            f"Command: {task.command}\n"
            f"Started: {task.started_at or 'Not yet started'}"
        )

    output = task.output or "(no output)"
    if task.error:
        output = f"{output}\n\nError: {task.error}"

    return output


@tool
def kill_hybrid_task(
    task_id: Annotated[str, "The ID of the task to kill"],
) -> str:
    """Kill a running background task.

    Args:
        task_id: The ID of the task to kill

    Returns:
        Success or error message
    """
    async def _kill():
        manager = get_hybrid_task_manager()
        result = await manager.kill(task_id)
        if result:
            return f"Task '{task_id}' killed successfully."
        else:
            return f"Could not kill task '{task_id}'. Task may not be running."

    return _run_async(_kill())


@tool
def run_hybrid_shell(
    command: Annotated[str, "The shell command to execute"],
    timeout: Annotated[int, "Maximum execution time in seconds (default: 900)"] = 900,
) -> str:
    """Run a shell command in the background.

    The command runs asynchronously and will not block the agent.
    Use list_hybrid_tasks to check status and get_hybrid_task_output to get results.

    Args:
        command: The shell command to execute
        timeout: Maximum execution time in seconds (default: 900 = 15 minutes)

    Returns:
        Task ID that can be used to check status and get output
    """
    async def _run():
        manager = get_hybrid_task_manager()
        task_id = await manager.run_shell(command, timeout=timeout)
        return f"Task '{task_id}' started for command: {command}"

    return _run_async(_run())


@tool
def run_hybrid_agent(
    prompt: Annotated[str, "The prompt to send to the agent"],
    timeout: Annotated[int, "Maximum execution time in seconds (default: 900)"] = 900,
) -> str:
    """Run an agent prompt in the background.

    The agent runs asynchronously and will not block the current agent.
    Use list_hybrid_tasks to check status and get_hybrid_task_output to get results.

    Args:
        prompt: The prompt to send to the agent
        timeout: Maximum execution time in seconds (default: 900 = 15 minutes)

    Returns:
        Task ID that can be used to check status and get output
    """
    async def _run():
        manager = get_hybrid_task_manager()
        task_id = await manager.run_agent(prompt, timeout=timeout)
        return f"Task '{task_id}' started for agent prompt: {prompt[:50]}..."

    return _run_async(_run())


@tool
def clear_hybrid_tasks() -> str:
    """Clear all completed background tasks.

    Removes all tasks that have completed, failed, been killed, or timed out.
    Running and queued tasks are not affected.

    Returns:
        Summary of cleared tasks
    """
    async def _clear():
        manager = get_hybrid_task_manager()
        count = await manager.clear_completed()
        return f"Cleared {count} completed task(s)."

    return _run_async(_clear())


# Collection of all hybrid task tools
HYBRID_TASK_TOOLS = [
    list_hybrid_tasks,
    get_hybrid_task_output,
    kill_hybrid_task,
    run_hybrid_shell,
    run_hybrid_agent,
    clear_hybrid_tasks,
]
