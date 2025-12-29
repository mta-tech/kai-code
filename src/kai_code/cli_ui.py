"""UI rendering and display utilities for the Rich CLI.

Adapted from deepagents-cli for kai-code.
"""

import json
import re
import shutil
from pathlib import Path
from typing import Any, Literal

from rich import box
from rich.markup import escape
from rich.panel import Panel
from rich.text import Text

from .rich_config import COLORS, COMMANDS, KAI_CODE_ASCII, MAX_ARG_LENGTH, console
from .file_ops import FileOperationRecord


def truncate_value(value: str, max_length: int = MAX_ARG_LENGTH) -> str:
    """Truncate a string value if it exceeds max_length."""
    if len(value) > max_length:
        return value[:max_length] + "..."
    return value


def format_tool_display(tool_name: str, tool_args: dict) -> str:
    """Format tool calls for display with tool-specific smart formatting.

    Shows the most relevant information for each tool type rather than all arguments.

    Args:
        tool_name: Name of the tool being called
        tool_args: Dictionary of tool arguments

    Returns:
        Formatted string for display (e.g., "read_file(config.py)")

    Examples:
        read_file(path="/long/path/file.py") -> "read_file(file.py)"
        web_search(query="how to code", max_results=5) -> 'web_search("how to code")'
        shell(command="pip install foo") -> 'shell("pip install foo")'
    """

    def abbreviate_path(path_str: str, max_length: int = 60) -> str:
        """Abbreviate a file path intelligently - show basename or relative path."""
        try:
            path = Path(path_str)

            # If it's just a filename (no directory parts), return as-is
            if len(path.parts) == 1:
                return path_str

            # Try to get relative path from current working directory
            try:
                rel_path = path.relative_to(Path.cwd())
                rel_str = str(rel_path)
                # Use relative if it's shorter and not too long
                if len(rel_str) < len(path_str) and len(rel_str) <= max_length:
                    return rel_str
            except (ValueError, Exception):
                pass

            # If absolute path is reasonable length, use it
            if len(path_str) <= max_length:
                return path_str

            # Otherwise, just show basename (filename only)
            return path.name
        except Exception:
            # Fallback to original string if any error
            return truncate_value(path_str, max_length)

    # Tool-specific formatting - show the most important argument(s)
    if tool_name in ("read_file", "write_file", "edit_file"):
        # File operations: show the primary file path argument (file_path or path)
        path_value = tool_args.get("file_path")
        if path_value is None:
            path_value = tool_args.get("path")
        if path_value is not None:
            path = abbreviate_path(str(path_value))
            return f"{tool_name}({path})"

    elif tool_name == "web_search":
        # Web search: show the query string
        if "query" in tool_args:
            query = str(tool_args["query"])
            query = truncate_value(query, 100)
            return f'{tool_name}("{query}")'

    elif tool_name == "grep":
        # Grep: show the search pattern
        if "pattern" in tool_args:
            pattern = str(tool_args["pattern"])
            pattern = truncate_value(pattern, 70)
            return f'{tool_name}("{pattern}")'

    elif tool_name in ("shell", "execute"):
        # Shell/Execute: show the command being executed
        if "command" in tool_args:
            command = str(tool_args["command"])
            command = truncate_value(command, 120)
            return f'{tool_name}("{command}")'

    elif tool_name == "ls":
        # ls: show directory, or empty if current directory
        if tool_args.get("path"):
            path = abbreviate_path(str(tool_args["path"]))
            return f"{tool_name}({path})"
        return f"{tool_name}()"

    elif tool_name == "glob":
        # Glob: show the pattern
        if "pattern" in tool_args:
            pattern = str(tool_args["pattern"])
            pattern = truncate_value(pattern, 80)
            return f'{tool_name}("{pattern}")'

    elif tool_name == "http_request":
        # HTTP: show method and URL
        parts = []
        if "method" in tool_args:
            parts.append(str(tool_args["method"]).upper())
        if "url" in tool_args:
            url = str(tool_args["url"])
            url = truncate_value(url, 80)
            parts.append(url)
        if parts:
            return f"{tool_name}({' '.join(parts)})"

    elif tool_name == "fetch_url":
        # Fetch URL: show the URL being fetched
        if "url" in tool_args:
            url = str(tool_args["url"])
            url = truncate_value(url, 80)
            return f'{tool_name}("{url}")'

    elif tool_name == "task":
        # Task: show the task description
        if "description" in tool_args:
            desc = str(tool_args["description"])
            desc = truncate_value(desc, 100)
            return f'{tool_name}("{desc}")'

    elif tool_name == "write_todos":
        # Todos: show count of items
        if "todos" in tool_args and isinstance(tool_args["todos"], list):
            count = len(tool_args["todos"])
            return f"{tool_name}({count} items)"

    # Fallback: generic formatting for unknown tools
    # Show all arguments in key=value format
    args_str = ", ".join(f"{k}={truncate_value(str(v), 50)}" for k, v in tool_args.items())
    return f"{tool_name}({args_str})"


def format_tool_message_content(content: Any) -> str:
    """Convert ToolMessage content into a printable string."""
    if content is None:
        return ""
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            else:
                try:
                    parts.append(json.dumps(item))
                except Exception:
                    parts.append(str(item))
        return "\n".join(parts)
    return str(content)


class TokenTracker:
    """Track token usage across the conversation."""

    # Threshold constants for context limit warnings
    WARNING_THRESHOLD = 0.80  # 80% - show warning
    CRITICAL_THRESHOLD = 0.95  # 95% - show critical warning

    def __init__(self) -> None:
        self.baseline_context = 0  # Baseline system context (system + agent.md + tools)
        self.current_context = 0  # Total context including messages
        self.last_output = 0
        self._context_limit: int | None = None  # Maximum context window size
        self._warned_80: bool = False  # Track if 80% warning has been shown
        self._warned_95: bool = False  # Track if 95% warning has been shown

    @property
    def context_limit(self) -> int | None:
        """Get the context limit for the current model."""
        return self._context_limit

    def set_context_limit(self, limit: int) -> None:
        """Set the context limit for the current model.

        Args:
            limit: The maximum context window size in tokens
        """
        self._context_limit = limit

    def get_usage_percentage(self) -> float | None:
        """Get the current context usage as a percentage.

        Returns:
            The usage percentage (0.0 to 1.0+) or None if no context limit is set
        """
        if self._context_limit is None or self._context_limit <= 0:
            return None
        return self.current_context / self._context_limit

    def get_status_level(self) -> Literal["normal", "warning", "critical", "unknown"]:
        """Get the current status level based on context usage.

        Returns:
            'unknown' - No context limit set
            'normal' - Usage < 80% (WARNING_THRESHOLD)
            'warning' - Usage >= 80% and < 95% (CRITICAL_THRESHOLD)
            'critical' - Usage >= 95%
        """
        percentage = self.get_usage_percentage()
        if percentage is None:
            return "unknown"
        if percentage >= self.CRITICAL_THRESHOLD:
            return "critical"
        if percentage >= self.WARNING_THRESHOLD:
            return "warning"
        return "normal"

    def should_show_warning(self) -> Literal["warning", "critical"] | None:
        """Check if a threshold warning should be shown.

        Returns the warning level if a threshold was just crossed for the first time,
        or None if no warning should be shown. Automatically marks the warning as shown.

        Returns:
            'warning' - First time crossing 80% threshold
            'critical' - First time crossing 95% threshold
            None - No new warning to show (either below thresholds or already warned)
        """
        percentage = self.get_usage_percentage()
        if percentage is None:
            return None

        # Check critical threshold first (95%)
        if percentage >= self.CRITICAL_THRESHOLD and not self._warned_95:
            self._warned_95 = True
            return "critical"

        # Check warning threshold (80%)
        if percentage >= self.WARNING_THRESHOLD and not self._warned_80:
            self._warned_80 = True
            return "warning"

        return None

    def _format_tokens_compact(self, tokens: int) -> str:
        """Format token count in compact K/M notation.

        Args:
            tokens: Token count to format

        Returns:
            Formatted string like '45K', '1.2M', '200K'
        """
        if tokens >= 1_000_000:
            # For millions, show 1 decimal place if not whole number
            value = tokens / 1_000_000
            if value == int(value):
                return f"{int(value)}M"
            return f"{value:.1f}M"
        elif tokens >= 1_000:
            # For thousands, show 1 decimal place if < 10K, otherwise whole number
            value = tokens / 1_000
            if value < 10 and value != int(value):
                return f"{value:.1f}K"
            return f"{int(value)}K"
        else:
            return str(tokens)

    def format_compact_display(self) -> str:
        """Format current token usage as a compact display string.

        Returns formatted strings based on context status:
        - Normal: '45K/200K [23%]'
        - Warning: '160K/200K ⚠️ 80%'
        - Critical: '190K/200K 🚨 95%'
        - Unknown (no limit): '45K tokens'

        Returns:
            Compact formatted string for status bar display
        """
        current = self._format_tokens_compact(self.current_context)

        if self._context_limit is None:
            # No limit set - just show current tokens
            return f"{current} tokens"

        limit = self._format_tokens_compact(self._context_limit)
        percentage = self.get_usage_percentage()
        status = self.get_status_level()

        if percentage is None:
            return f"{current}/{limit}"

        percent_int = int(percentage * 100)

        if status == "critical":
            return f"{current}/{limit} 🚨 {percent_int}%"
        elif status == "warning":
            return f"{current}/{limit} ⚠️ {percent_int}%"
        else:
            return f"{current}/{limit} [{percent_int}%]"

    def set_baseline(self, tokens: int) -> None:
        """Set the baseline context token count.

        Args:
            tokens: The baseline token count (system prompt + agent.md + tools)
        """
        self.baseline_context = tokens
        self.current_context = tokens

    def reset(self) -> None:
        """Reset to baseline (for /clear command)."""
        self.current_context = self.baseline_context
        self.last_output = 0
        self._warned_80 = False
        self._warned_95 = False

    def add(self, input_tokens: int, output_tokens: int) -> None:
        """Add tokens from a response."""
        # input_tokens IS the current context size (what was sent to the model)
        self.current_context = input_tokens
        self.last_output = output_tokens

    def display_last(self) -> None:
        """Display current context size after this turn."""
        if self.last_output and self.last_output >= 1000:
            console.print(f"  Generated: {self.last_output:,} tokens", style="dim")
        if self.current_context:
            console.print(f"  Current context: {self.current_context:,} tokens", style="dim")

    def display_session(self) -> None:
        """Display current context size."""
        console.print("\n[bold]Token Usage:[/bold]", style=COLORS["primary"])

        # Check if we've had any actual API calls yet (current > baseline means we have conversation)
        has_conversation = self.current_context > self.baseline_context

        if self.baseline_context > 0:
            console.print(
                f"  Baseline: {self.baseline_context:,} tokens [dim](system + agent.md)[/dim]",
                style=COLORS["dim"],
            )

            if not has_conversation:
                # Before first message - warn that tools aren't counted yet
                console.print(
                    "  [dim]Note: Tool definitions (~5k tokens) included after first message[/dim]"
                )

        if has_conversation:
            tools_and_conversation = self.current_context - self.baseline_context
            console.print(
                f"  Tools + conversation: {tools_and_conversation:,} tokens", style=COLORS["dim"]
            )

        console.print(f"  Total: {self.current_context:,} tokens", style="bold " + COLORS["dim"])
        console.print()


def render_todo_list(todos: list[dict]) -> None:
    """Render todo list as a rich Panel with checkboxes."""
    if not todos:
        return

    lines = []
    for todo in todos:
        status = todo.get("status", "pending")
        content = todo.get("content", "")

        if status == "completed":
            icon = "[green]v[/green]"
            style = "green"
        elif status == "in_progress":
            icon = "[yellow]>[/yellow]"
            style = "yellow"
        else:  # pending
            icon = "[dim]o[/dim]"
            style = "dim"

        lines.append(f"[{style}]{icon} {content}[/{style}]")

    panel = Panel(
        "\n".join(lines),
        title="[bold]Task List[/bold]",
        border_style="cyan",
        box=box.ROUNDED,
        padding=(0, 1),
    )
    console.print(panel)


def _format_line_span(start: int | None, end: int | None) -> str:
    if start is None and end is None:
        return ""
    if start is not None and end is None:
        return f"(starting at line {start})"
    if start is None and end is not None:
        return f"(through line {end})"
    if start == end:
        return f"(line {start})"
    return f"(lines {start}-{end})"


def render_file_operation(record: FileOperationRecord) -> None:
    """Render a concise summary of a filesystem tool call."""
    label_lookup = {
        "read_file": "Read",
        "write_file": "Write",
        "edit_file": "Update",
    }
    label = label_lookup.get(record.tool_name, record.tool_name)
    header = Text()
    header.append("* ", style=COLORS["tool"])
    header.append(f"{label}({record.display_path})", style=f"bold {COLORS['tool']}")
    console.print(header)

    def _print_detail(message: str, *, style: str = COLORS["dim"]) -> None:
        detail = Text()
        detail.append("  |  ", style=style)
        detail.append(message, style=style)
        console.print(detail)

    if record.status == "error":
        _print_detail(record.error or "Error executing file operation", style="red")
        return

    if record.tool_name == "read_file":
        lines = record.metrics.lines_read
        span = _format_line_span(record.metrics.start_line, record.metrics.end_line)
        detail = f"Read {lines} line{'s' if lines != 1 else ''}"
        if span:
            detail = f"{detail} {span}"
        _print_detail(detail)
    else:
        if record.tool_name == "write_file":
            added = record.metrics.lines_added
            removed = record.metrics.lines_removed
            lines = record.metrics.lines_written
            detail = f"Wrote {lines} line{'s' if lines != 1 else ''}"
            if added or removed:
                detail = f"{detail} (+{added} / -{removed})"
        else:
            added = record.metrics.lines_added
            removed = record.metrics.lines_removed
            detail = f"Edited {record.metrics.lines_written} total line{'s' if record.metrics.lines_written != 1 else ''}"
            if added or removed:
                detail = f"{detail} (+{added} / -{removed})"
        _print_detail(detail)

    # Skip diff display for HIL-approved operations that succeeded
    # (user already saw the diff during approval)
    if record.diff and not (record.hitl_approved and record.status == "success"):
        render_diff(record)


def render_diff(record: FileOperationRecord) -> None:
    """Render diff for a file operation."""
    if not record.diff:
        return
    render_diff_block(record.diff, f"Diff {record.display_path}")


def _wrap_diff_line(
    code: str,
    marker: str,
    color: str,
    line_num: int | None,
    width: int,
    term_width: int,
) -> list[str]:
    """Wrap long diff lines with proper indentation.

    Args:
        code: Code content to wrap
        marker: Diff marker ('+', '-', ' ')
        color: Color for the line
        line_num: Line number to display (None for continuation lines)
        width: Width for line number column
        term_width: Terminal width

    Returns:
        List of formatted lines (may be multiple if wrapped)
    """
    # Escape Rich markup in code content
    code = escape(code)

    prefix_len = width + 4  # line_num + space + marker + 2 spaces
    available_width = term_width - prefix_len

    if len(code) <= available_width:
        if line_num is not None:
            return [f"[dim]{line_num:>{width}}[/dim] [{color}]{marker}  {code}[/{color}]"]
        return [f"{' ' * width} [{color}]{marker}  {code}[/{color}]"]

    lines = []
    remaining = code
    first = True

    while remaining:
        if len(remaining) <= available_width:
            chunk = remaining
            remaining = ""
        else:
            # Try to break at a good point (space, comma, etc.)
            chunk = remaining[:available_width]
            # Look for a good break point in the last 20 chars
            break_point = max(
                chunk.rfind(" "),
                chunk.rfind(","),
                chunk.rfind("("),
                chunk.rfind(")"),
            )
            if break_point > available_width - 20:
                # Found a good break point
                chunk = remaining[: break_point + 1]
                remaining = remaining[break_point + 1 :]
            else:
                # No good break point, just split
                chunk = remaining[:available_width]
                remaining = remaining[available_width:]

        if first and line_num is not None:
            lines.append(f"[dim]{line_num:>{width}}[/dim] [{color}]{marker}  {chunk}[/{color}]")
            first = False
        else:
            lines.append(f"{' ' * width} [{color}]{marker}  {chunk}[/{color}]")

    return lines


def format_diff_rich(diff_lines: list[str]) -> str:
    """Format diff lines with line numbers and colors.

    Args:
        diff_lines: Diff lines from unified diff

    Returns:
        Rich-formatted diff string with line numbers
    """
    if not diff_lines:
        return "[dim]No changes detected[/dim]"

    # Get terminal width
    term_width = shutil.get_terminal_size().columns

    # Find max line number for width calculation
    max_line = max(
        (
            int(m.group(i))
            for line in diff_lines
            if (m := re.match(r"@@ -(\d+)(?:,\d+)? \+(\d+)", line))
            for i in (1, 2)
        ),
        default=0,
    )
    width = max(3, len(str(max_line)))

    formatted_lines = []
    old_num = new_num = 0

    # Rich colors with backgrounds for better visibility
    # White text on dark backgrounds for additions/deletions
    addition_color = "white on dark_green"
    deletion_color = "white on dark_red"
    context_color = "dim"

    for line in diff_lines:
        if line.strip() == "...":
            formatted_lines.append(f"[{context_color}]...[/{context_color}]")
        elif line.startswith(("---", "+++")):
            continue
        elif m := re.match(r"@@ -(\d+)(?:,\d+)? \+(\d+)", line):
            old_num, new_num = int(m.group(1)), int(m.group(2))
        elif line.startswith("-"):
            formatted_lines.extend(
                _wrap_diff_line(line[1:], "-", deletion_color, old_num, width, term_width)
            )
            old_num += 1
        elif line.startswith("+"):
            formatted_lines.extend(
                _wrap_diff_line(line[1:], "+", addition_color, new_num, width, term_width)
            )
            new_num += 1
        elif line.startswith(" "):
            formatted_lines.extend(
                _wrap_diff_line(line[1:], " ", context_color, old_num, width, term_width)
            )
            old_num += 1
            new_num += 1

    return "\n".join(formatted_lines)


def render_diff_block(diff: str, title: str) -> None:
    """Render a diff string with line numbers and colors."""
    try:
        # Parse diff into lines and format with line numbers
        diff_lines = diff.splitlines()
        formatted_diff = format_diff_rich(diff_lines)

        # Print with a simple header
        console.print()
        console.print(f"[bold {COLORS['primary']}]=== {title} ===[/bold {COLORS['primary']}]")
        console.print(formatted_diff)
        console.print()
    except (ValueError, AttributeError, IndexError, OSError):
        # Fallback to simple rendering if formatting fails
        console.print()
        console.print(f"[bold {COLORS['primary']}]{title}[/bold {COLORS['primary']}]")
        console.print(diff)
        console.print()


def show_interactive_help() -> None:
    """Show available commands during interactive session."""
    console.print()
    console.print("[bold]Interactive Commands:[/bold]", style=COLORS["primary"])
    console.print()

    for cmd, desc in COMMANDS.items():
        console.print(f"  /{cmd:<12} {desc}", style=COLORS["dim"])

    console.print()
    console.print("[bold]Editing Features:[/bold]", style=COLORS["primary"])
    console.print("  Enter           Submit your message", style=COLORS["dim"])
    console.print(
        "  Alt+Enter       Insert newline (Option+Enter on Mac, or ESC then Enter)",
        style=COLORS["dim"],
    )
    console.print(
        "  Ctrl+E          Open in external editor (nano by default)", style=COLORS["dim"]
    )
    console.print("  Ctrl+T          Toggle auto-approve mode", style=COLORS["dim"])
    console.print("  Arrow keys      Navigate input", style=COLORS["dim"])
    console.print("  Ctrl+C          Cancel input or interrupt agent mid-work", style=COLORS["dim"])
    console.print()
    console.print("[bold]Special Features:[/bold]", style=COLORS["primary"])
    console.print(
        "  @filename       Type @ to auto-complete files and inject content", style=COLORS["dim"]
    )
    console.print("  /command        Type / to see available commands", style=COLORS["dim"])
    console.print(
        "  !command        Type ! to run bash commands (e.g., !ls, !git status)",
        style=COLORS["dim"],
    )
    console.print(
        "                  Completions appear automatically as you type", style=COLORS["dim"]
    )
    console.print()
    console.print("[bold]Auto-Approve Mode:[/bold]", style=COLORS["primary"])
    console.print("  Ctrl+T          Toggle auto-approve mode", style=COLORS["dim"])
    console.print(
        "  --auto-approve  Start CLI with auto-approve enabled (via command line)",
        style=COLORS["dim"],
    )
    console.print(
        "  When enabled, tool actions execute without confirmation prompts", style=COLORS["dim"]
    )
    console.print()


def show_help() -> None:
    """Show help information."""
    console.print()
    console.print(KAI_CODE_ASCII, style=f"bold {COLORS['primary']}")
    console.print()

    console.print("[bold]Usage:[/bold]", style=COLORS["primary"])
    console.print("  kai [OPTIONS]                           Start interactive session")
    console.print("  kai -p PROMPT                           Run prompt directly (headless)")
    console.print("  kai help                                Show this help message")
    console.print()

    console.print("[bold]Options:[/bold]", style=COLORS["primary"])
    console.print("  -p, --prompt PROMPT       Prompt to run (headless mode)")
    console.print("  -y, --yes                 Auto-approve all actions (YOLO mode)")
    console.print("  --model MODEL             Model to use (e.g., sonnet-4.5, gpt-4o)")
    console.print("  --new                     Start a fresh session")
    console.print("  --dry-run                 Print resolved config without calling model")
    console.print()

    console.print("[bold]Examples:[/bold]", style=COLORS["primary"])
    console.print(
        "  kai                              # Start interactive session", style=COLORS["dim"]
    )
    console.print(
        "  kai -y                           # Start with auto-approve",
        style=COLORS["dim"],
    )
    console.print(
        "  kai -p 'hello world'             # Run prompt directly",
        style=COLORS["dim"],
    )
    console.print(
        "  kai --new                        # Start fresh session",
        style=COLORS["dim"],
    )
    console.print()

    console.print("[bold]Interactive Features:[/bold]", style=COLORS["primary"])
    console.print("  Enter           Submit your message", style=COLORS["dim"])
    console.print(
        "  Alt+Enter       Insert newline for multi-line (Option+Enter or ESC then Enter)",
        style=COLORS["dim"],
    )
    console.print("  Ctrl+J          Insert newline (alternative)", style=COLORS["dim"])
    console.print("  Ctrl+T          Toggle auto-approve mode", style=COLORS["dim"])
    console.print("  Arrow keys      Navigate input", style=COLORS["dim"])
    console.print(
        "  @filename       Type @ to auto-complete files and inject content", style=COLORS["dim"]
    )
    console.print(
        "  /command        Type / to see available commands (auto-completes)", style=COLORS["dim"]
    )
    console.print()

    console.print("[bold]Interactive Commands:[/bold]", style=COLORS["primary"])
    console.print("  /help           Show available commands and features", style=COLORS["dim"])
    console.print("  /clear          Clear screen and reset conversation", style=COLORS["dim"])
    console.print("  /tokens         Show token usage for current session", style=COLORS["dim"])
    console.print("  /quit, /exit    Exit the session", style=COLORS["dim"])
    console.print(
        "  quit, exit, q   Exit the session (just type and press Enter)", style=COLORS["dim"]
    )
    console.print()

    console.print("[bold]Settings Commands:[/bold]", style=COLORS["primary"])
    console.print(
        "  /export-settings [file]           Export settings to JSON (default: kai-settings.json)",
        style=COLORS["dim"],
    )
    console.print(
        "  /import-settings <file> [--target global|project|local]",
        style=COLORS["dim"],
    )
    console.print(
        "                                    Import settings from JSON (default: project)",
        style=COLORS["dim"],
    )
    console.print()
