"""Helper functions for consistent Rich CLI formatting.

Provides standardized formatting for sections, status indicators,
errors, progress bars, and step-by-step output.
"""

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.text import Text

# Use global console instance from rich_config
from kai_code.rich_config import console, COLORS


def print_section_header(title: str) -> None:
    """Print a section header with border and title.

    Args:
        title: Section title to display
    """
    # Calculate border width based on terminal or default to 60
    width = 60
    border = "═" * width

    console.print()
    console.print(border, style=COLORS["primary"])
    console.print(f"[bold {COLORS['primary']}]{title}[/bold {COLORS['primary']}]")
    console.print(border, style=COLORS["primary"])
    console.print()


STATUS_ICONS = {
    "success": "✓",
    "warning": "⚠️",
    "error": "✗",
    "info": "ℹ️",
    "processing": "⏳",
}

STATUS_COLORS = {
    "success": "green",
    "warning": "yellow",
    "error": "red",
    "info": "blue",
    "processing": "blue",
}


def print_status(status: str, message: str, icon: str | None = None) -> None:
    """Print a status message with icon and color.

    Args:
        status: Status type (success, warning, error, info, processing)
        message: Status message to display
        icon: Optional custom icon (uses default if not provided)
    """
    icon = icon or STATUS_ICONS.get(status, "•")
    color = STATUS_COLORS.get(status, "white")

    console.print(f"[{color}]{icon}  {message}[/{color}]")


def print_error(error: str, suggestion: str | None = None) -> None:
    """Print an error with optional suggestion.

    Args:
        error: Error message
        suggestion: Optional suggestion for fixing the error
    """
    console.print()
    console.print(f"[red]✗ {error}[/red]")
    if suggestion:
        console.print(f"  └─ [dim]Suggestion: {suggestion}[/dim]")
    console.print()


def format_progress(current: int, total: int) -> str:
    """Format progress as string.

    Args:
        current: Current progress value
        total: Total value

    Returns:
        Formatted progress string (e.g., "75% (3/4)")
    """
    if total == 0:
        return "0% (0/0)"

    percentage = int((current / total) * 100)
    return f"{percentage}% ({current}/{total})"


def print_step(number: int, description: str, result: str | None = None) -> None:
    """Print a step with number, description, and optional result.

    Args:
        number: Step number
        description: Step description
        result: Optional result to display indented
    """
    console.print(f"[bold {COLORS['primary']}]({number})[/bold {COLORS['primary']}] {description}")

    if result:
        console.print(f"    {result}")


def print_summary(results: dict[str, bool]) -> None:
    """Print a summary of test/task results.

    Args:
        results: Dictionary mapping test names to pass/fail (True/False)
    """
    print_section_header("Summary")

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for name, success in results.items():
        status_icon = "✓" if success else "✗"
        status_color = "green" if success else "red"
        status_text = "PASSED" if success else "FAILED"
        console.print(f"[{status_color}]{status_icon}  {name:30s} {status_text}[/ {status_color}]")

    console.print()
    if passed == total:
        console.print(f"[green]Result: {passed}/{total} tests passed {'✓' * passed}[/green]")
    else:
        console.print(f"[yellow]Result: {passed}/{total} tests passed ({total - passed} failed)[/yellow]")
    console.print()
