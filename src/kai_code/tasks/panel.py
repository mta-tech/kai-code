"""Rich-based UI panel for viewing and managing background tasks."""
from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.box import ROUNDED

if TYPE_CHECKING:
    from .task import Task

from .manager import get_task_manager
from .task import TaskStatus

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
}


def _format_task_row(task: "Task", selected: bool = False) -> tuple[str, str, str]:
    """Format a task for display in the table.

    Args:
        task: The task to format
        selected: Whether this task is selected

    Returns:
        Tuple of (prefix, description, status)
    """
    prefix = ">" if selected else " "

    # Priority indicator (e.g., [H] for high, [L] for low)
    priority_indicator = task.priority_indicator

    # Description with priority indicator (truncated)
    desc = task.description
    # Account for priority indicator length when truncating
    max_desc_len = 50 - len(priority_indicator)
    if len(desc) > max_desc_len:
        desc = desc[:max_desc_len - 3] + "..."
    desc = priority_indicator + desc

    # Status with color
    status_text = task.display_status

    return prefix, desc, status_text


def _get_status_style(status: TaskStatus) -> str:
    """Get Rich style for a task status."""
    if status == TaskStatus.RUNNING:
        return COLORS["running"]
    elif status == TaskStatus.COMPLETED:
        return COLORS["completed"]
    elif status == TaskStatus.FAILED:
        return COLORS["failed"]
    elif status == TaskStatus.KILLED:
        return COLORS["dim"]
    elif status == TaskStatus.QUEUED:
        return COLORS["queued"]
    return COLORS["dim"]


def show_tasks_panel(interactive: bool = True) -> None:
    """Display the background tasks panel.

    Args:
        interactive: If True, allow keyboard navigation
    """
    manager = get_task_manager()
    tasks = manager.get_all_tasks()

    if not tasks:
        console.print()
        console.print("[dim]No background tasks.[/dim]")
        console.print()
        return

    if interactive:
        _interactive_panel(tasks)
    else:
        _static_panel(tasks)


def _static_panel(tasks: list["Task"]) -> None:
    """Display a static (non-interactive) view of tasks."""
    manager = get_task_manager()
    # Running tasks (not queued)
    running = [t for t in tasks if t.status == TaskStatus.RUNNING]
    # Queued tasks
    queued = manager.get_queued_tasks()
    completed = manager.get_completed_tasks()

    # Create table
    table = Table(show_header=False, box=None, padding=(0, 1))
    table.add_column("Prefix", style="bold", width=2)
    table.add_column("Description", min_width=40)
    table.add_column("Status", justify="right", width=20)

    # Running tasks
    if running:
        table.add_row("", Text("Running", style="bold"), "")
        for task in running:
            _, desc, status = _format_task_row(task)
            table.add_row("", desc, Text(status, style=_get_status_style(task.status)))
        table.add_row("", "", "")

    # Queued tasks
    if queued:
        table.add_row("", Text("Queued", style=f"bold {COLORS['queued']}"), "")
        for task in queued:
            _, desc, status = _format_task_row(task)
            table.add_row("", desc, Text(status, style=_get_status_style(task.status)))
        table.add_row("", "", "")

    # Completed tasks
    if completed:
        table.add_row("", Text("Completed", style="bold dim"), "")
        for task in completed:
            _, desc, status = _format_task_row(task)
            table.add_row("", desc, Text(status, style=_get_status_style(task.status)))

    # Summary line with queued count
    active_count = len(running)
    queued_count = len(queued)
    summary_parts = [f"{active_count} running"]
    if queued_count > 0:
        summary_parts.append(f"{queued_count} queued")
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


def _interactive_panel(tasks: list["Task"]) -> None:
    """Display an interactive task panel with keyboard navigation."""
    manager = get_task_manager()
    selected_idx = 0
    viewing_output = False

    try:
        import termios
        import tty

        # Save terminal settings
        old_settings = termios.tcgetattr(sys.stdin)

        try:
            # Set terminal to raw mode for key capture
            tty.setcbreak(sys.stdin.fileno())

            while True:
                # Refresh task list
                tasks = manager.get_all_tasks()

                if not tasks:
                    console.clear()
                    console.print()
                    console.print("[dim]No background tasks.[/dim]")
                    console.print()
                    break

                # Clamp selection
                selected_idx = max(0, min(selected_idx, len(tasks) - 1))
                selected_task = tasks[selected_idx]

                if viewing_output:
                    _render_output_view(selected_task)
                else:
                    _render_task_list(tasks, selected_idx)

                # Read key
                key = sys.stdin.read(1)

                if key == '\x1b':  # Escape sequence
                    # Read additional bytes for arrow keys
                    next1 = sys.stdin.read(1)
                    if next1 == '[':
                        next2 = sys.stdin.read(1)
                        if next2 == 'A':  # Up arrow
                            if not viewing_output:
                                selected_idx = max(0, selected_idx - 1)
                        elif next2 == 'B':  # Down arrow
                            if not viewing_output:
                                selected_idx = min(len(tasks) - 1, selected_idx + 1)
                    else:
                        # Plain Escape - back or close
                        if viewing_output:
                            viewing_output = False
                        else:
                            break
                elif key == '\r' or key == '\n':  # Enter
                    if not viewing_output:
                        viewing_output = True
                elif key == 'q':
                    break
                elif key == 'k':  # Kill task
                    if not viewing_output and selected_task.status == TaskStatus.RUNNING:
                        manager.kill_task(selected_task.id)
                elif key == 'c':  # Clear completed
                    if not viewing_output:
                        manager.clear_completed()
                        selected_idx = 0

        finally:
            # Restore terminal settings
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
            console.clear()

    except ImportError:
        # Fall back to static view on Windows or if termios not available
        _static_panel(tasks)


def _render_task_list(tasks: list["Task"], selected_idx: int) -> None:
    """Render the task list view."""
    console.clear()

    manager = get_task_manager()
    # Running tasks (not queued)
    running = [t for t in tasks if t.status == TaskStatus.RUNNING]
    # Queued tasks
    queued = manager.get_queued_tasks()
    completed = [t for t in tasks if t.status not in (TaskStatus.PENDING, TaskStatus.RUNNING, TaskStatus.QUEUED)]

    # Build table
    table = Table(show_header=False, box=None, padding=(0, 1))
    table.add_column("Prefix", style="bold cyan", width=2)
    table.add_column("Description", min_width=45)
    table.add_column("Status", justify="right", width=20)

    idx = 0

    # Running section
    if running:
        table.add_row("", Text(f"Running ({len(running)})", style="bold"), "")
        for task in running:
            is_selected = idx == selected_idx
            prefix, desc, status = _format_task_row(task, is_selected)

            if is_selected:
                table.add_row(
                    Text(prefix, style="bold cyan"),
                    Text(desc, style="bold"),
                    Text(status, style=f"bold {_get_status_style(task.status)}")
                )
            else:
                table.add_row(
                    prefix,
                    desc,
                    Text(status, style=_get_status_style(task.status))
                )
            idx += 1
        table.add_row("", "", "")

    # Queued section
    if queued:
        table.add_row("", Text(f"Queued ({len(queued)})", style=f"bold {COLORS['queued']}"), "")
        for task in queued:
            is_selected = idx == selected_idx
            prefix, desc, status = _format_task_row(task, is_selected)

            if is_selected:
                table.add_row(
                    Text(prefix, style="bold cyan"),
                    Text(desc, style="bold"),
                    Text(status, style=f"bold {_get_status_style(task.status)}")
                )
            else:
                table.add_row(
                    prefix,
                    desc,
                    Text(status, style=_get_status_style(task.status))
                )
            idx += 1
        table.add_row("", "", "")

    # Completed section
    if completed:
        table.add_row("", Text(f"Completed ({len(completed)})", style="bold dim"), "")
        for task in completed:
            is_selected = idx == selected_idx
            prefix, desc, status = _format_task_row(task, is_selected)

            if is_selected:
                table.add_row(
                    Text(prefix, style="bold cyan"),
                    Text(desc, style="bold"),
                    Text(status, style=f"bold {_get_status_style(task.status)}")
                )
            else:
                table.add_row(
                    prefix,
                    Text(desc, style="dim"),
                    Text(status, style=_get_status_style(task.status))
                )
            idx += 1

    # Summary with queued count
    running_count = len(running)
    queued_count = len(queued)
    summary_parts = [f"{running_count} running"]
    if queued_count > 0:
        summary_parts.append(f"{queued_count} queued")
    summary_parts.append(f"{len(completed)} completed")
    summary = ", ".join(summary_parts)

    # Help line
    help_text = Text()
    help_text.append("↑/↓ ", style="dim")
    help_text.append("select", style="dim")
    help_text.append(" · ", style="dim")
    help_text.append("Enter ", style="dim")
    help_text.append("view", style="dim")
    help_text.append(" · ", style="dim")
    help_text.append("k ", style="dim")
    help_text.append("kill", style="dim")
    help_text.append(" · ", style="dim")
    help_text.append("c ", style="dim")
    help_text.append("clear", style="dim")
    help_text.append(" · ", style="dim")
    help_text.append("Esc ", style="dim")
    help_text.append("close", style="dim")

    content = Group(table, Text(), help_text)

    panel = Panel(
        content,
        title="Background Tasks",
        subtitle=summary,
        border_style=COLORS["primary"],
        box=ROUNDED,
    )

    console.print()
    console.print(panel)


def _render_output_view(task: "Task") -> None:
    """Render the output view for a single task."""
    console.clear()

    # Truncate output for display
    output = task.output or "(no output)"
    max_lines = 30
    lines = output.split('\n')
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines.append(f"... ({len(output.split(chr(10))) - max_lines} more lines)")
    output = '\n'.join(lines)

    # Help line
    help_text = Text()
    help_text.append("Esc ", style="dim")
    help_text.append("back", style="dim")
    help_text.append(" · ", style="dim")
    help_text.append("q ", style="dim")
    help_text.append("close", style="dim")

    content = Group(Text(output, style=""), Text(), help_text)

    # Title with task description
    title = task.description
    if len(title) > 50:
        title = title[:47] + "..."

    panel = Panel(
        content,
        title=f"Output: {title}",
        subtitle=task.display_status,
        border_style=_get_status_style(task.status),
        box=ROUNDED,
    )

    console.print()
    console.print(panel)


def format_task_status_line() -> str | None:
    """Get a status line for the prompt showing active task count.

    Returns:
        Status string like "2 tasks" or None if no active tasks
    """
    manager = get_task_manager()
    active = manager.active_count()

    if active == 0:
        return None

    return f"{active} task{'s' if active != 1 else ''}"


def format_tasks_summary() -> str:
    """Get a summary of all tasks for display.

    Returns:
        Formatted string summary of tasks
    """
    manager = get_task_manager()
    tasks = manager.get_all_tasks()

    if not tasks:
        return "No background tasks."

    lines = []
    # Running tasks (not queued)
    running = [t for t in tasks if t.status == TaskStatus.RUNNING]
    queued = manager.get_queued_tasks()
    completed = manager.get_completed_tasks()

    # Build summary line with queued count
    summary_parts = [f"{len(running)} running"]
    if len(queued) > 0:
        summary_parts.append(f"{len(queued)} queued")
    summary_parts.append(f"{len(completed)} completed")
    lines.append(f"Background Tasks: {', '.join(summary_parts)}")
    lines.append("")

    for task in tasks[:10]:
        status_icon = {
            TaskStatus.RUNNING: "⟳",
            TaskStatus.COMPLETED: "✓",
            TaskStatus.FAILED: "✗",
            TaskStatus.KILLED: "○",
            TaskStatus.PENDING: "·",
            TaskStatus.QUEUED: "⏳",
        }.get(task.status, "?")

        lines.append(f"  {status_icon} [{task.id}] {task.description}")

    if len(tasks) > 10:
        lines.append(f"  ... and {len(tasks) - 10} more")

    return "\n".join(lines)
