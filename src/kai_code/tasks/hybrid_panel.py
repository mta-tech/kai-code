"""Rich-based UI panel for the hybrid async/thread task manager.

This provides a static display for HybridTaskManager tasks.
For live updates, use Rich Live display in your application.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.box import ROUNDED

if TYPE_CHECKING:
    from .hybrid_manager import Task, TaskStatus

console = Console(highlight=False)

# Colors matching the main CLI
COLORS = {
    "primary": "#10b981",
    "dim": "#6b7280",
    "running": "#fbbf24",
    "completed": "#10b981",
    "failed": "#ef4444",
    "killed": "#6b7280",
    "queued": "#60a5fa",
    "timed_out": "#f59e0b",
}


def _get_status_emoji(status: "TaskStatus") -> str:
    """Get emoji for task status."""
    emojis = {
        "queued": "[60a5fa]⏳[/60a5fa]",
        "running": "[fbbf24]⟳[/fbbf24]",
        "completed": "[10b981]✓[/10b981]",
        "failed": "[ef4444]✗[/ef4444]",
        "killed": "[6b7280]⏹[/6b7280]",
        "timed_out": "[f59e0b]⏱[/f59e0b]",
    }
    return emojis.get(status.value, "?")


def _format_duration(task: "Task") -> str:
    """Format task duration string."""
    if task.status.value == "queued":
        return "queued"
    elif task.status.value == "running" and task.started_at:
        from datetime import datetime
        elapsed = (datetime.now() - task.started_at).total_seconds()
        return f"{elapsed:.1f}s"
    elif task.finished_at and task.started_at:
        elapsed = (task.finished_at - task.started_at).total_seconds()
        return f"done ({elapsed:.1f}s)"
    return "unknown"


def _get_status_style(status: "TaskStatus") -> str:
    """Get Rich style for a task status."""
    status_map = {
        "queued": COLORS["queued"],
        "running": COLORS["running"],
        "completed": COLORS["completed"],
        "failed": COLORS["failed"],
        "killed": COLORS["killed"],
        "timed_out": COLORS["timed_out"],
    }
    return status_map.get(status.value, COLORS["dim"])


def show_hybrid_tasks_panel(manager, interactive: bool = False) -> None:
    """Display the background tasks panel for HybridTaskManager.

    Args:
        manager: HybridTaskManager instance
        interactive: If True, allow keyboard navigation (not yet implemented)
    """
    tasks = manager.get_all_tasks()

    if not tasks:
        console.print()
        console.print("[dim]No background tasks.[/dim]")
        console.print()
        return

    _static_panel(tasks, manager)


def _static_panel(tasks: list["Task"], manager) -> None:
    """Display a static (non-interactive) view of tasks."""
    # Group tasks by status
    queued = [t for t in tasks if t.status.value == "queued"]
    running = [t for t in tasks if t.status.value == "running"]
    completed = [
        t for t in tasks
        if t.status.value in ("completed", "failed", "killed", "timed_out")
    ]

    # Create table
    table = Table(show_header=True, box=None, padding=(0, 1))
    table.add_column("ID", style="cyan", width=8)
    table.add_column("Status", justify="left", width=15)
    table.add_column("Command", min_width=40)
    table.add_column("Duration", justify="right", width=15)

    # Running tasks
    if running:
        for task in running:
            table.add_row(
                task.id,
                Text(_get_status_emoji(task.status)),
                Text(task.command[:50] + "..." if len(task.command) > 50 else task.command),
                Text(_format_duration(task), style=COLORS["running"]),
            )

    # Queued tasks
    if queued:
        for task in queued:
            table.add_row(
                task.id,
                Text(_get_status_emoji(task.status)),
                Text(task.command[:50] + "..." if len(task.command) > 50 else task.command),
                Text(_format_duration(task), style=COLORS["queued"]),
            )

    # Completed tasks
    if completed:
        for task in completed:
            table.add_row(
                task.id,
                Text(_get_status_emoji(task.status)),
                Text(task.command[:50] + "..." if len(task.command) > 50 else task.command),
                Text(_format_duration(task), style=_get_status_style(task.status)),
            )

    # Summary line
    summary_parts = [f"{len(running)} running"]
    if len(queued) > 0:
        summary_parts.append(f"{len(queued)} queued")
    summary_parts.append(f"{len(completed)} completed")
    summary = ", ".join(summary_parts)

    panel = Panel(
        table,
        title="Background Tasks",
        subtitle=summary,
        border_style=COLORS["primary"],
        box=ROUNDED,
    )

    console.print()
    console.print(panel)
    console.print()


def format_hybrid_task_status_line(manager) -> str | None:
    """Get a status line for the prompt showing active task count.

    Args:
        manager: HybridTaskManager instance

    Returns:
        Status string like "2 tasks" or None if no active tasks
    """
    active = manager.active_count()

    if active == 0:
        return None

    return f"{active} task{'s' if active != 1 else ''}"


def format_hybrid_tasks_summary(manager) -> str:
    """Get a summary of all tasks for display.

    Args:
        manager: HybridTaskManager instance

    Returns:
        Formatted string summary of tasks
    """
    tasks = manager.get_all_tasks()

    if not tasks:
        return "No background tasks."

    lines = []
    queued = [t for t in tasks if t.status.value == "queued"]
    running = [t for t in tasks if t.status.value == "running"]
    completed = [
        t for t in tasks
        if t.status.value in ("completed", "failed", "killed", "timed_out")
    ]

    # Build summary line
    summary_parts = [f"{len(running)} running"]
    if len(queued) > 0:
        summary_parts.append(f"{len(queued)} queued")
    summary_parts.append(f"{len(completed)} completed")
    lines.append(f"Background Tasks: {', '.join(summary_parts)}")
    lines.append("")

    for task in tasks[:10]:
        status_icon = {
            "queued": "⏳",
            "running": "⟳",
            "completed": "✓",
            "failed": "✗",
            "killed": "○",
            "timed_out": "⏱",
        }.get(task.status.value, "?")

        lines.append(f"  {status_icon} [{task.id}] {task.command[:50]}")

    if len(tasks) > 10:
        lines.append(f"  ... and {len(tasks) - 10} more")

    return "\n".join(lines)
