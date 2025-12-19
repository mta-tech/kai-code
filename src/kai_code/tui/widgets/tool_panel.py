"""Tool panel widget for TUI."""

from enum import Enum
from textual.widgets import Static
from textual.containers import Vertical
from rich.panel import Panel
from rich.text import Text
from rich.syntax import Syntax
import time


class ToolStatus(Enum):
    """Tool execution status."""
    IDLE = "idle"
    RUNNING = "running"
    COMPLETE = "complete"
    ERROR = "error"


class ToolPanel(Vertical):
    """Right-side panel showing tool status and output."""

    DEFAULT_CSS = """
    ToolPanel {
        width: 35%;
        height: 100%;
        border-left: solid $primary;
    }

    ToolPanel .tool-status {
        height: auto;
        padding: 1;
    }

    ToolPanel .tool-output {
        height: 1fr;
        padding: 1;
        overflow-y: auto;
    }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.status = ToolStatus.IDLE
        self.tool_name: str | None = None
        self.tool_args: dict | None = None
        self.exit_code: int | None = None
        self._start_time: float | None = None
        self._result: str | None = None

    def compose(self):
        """Compose the panel layout."""
        yield Static("", classes="tool-status", id="tool-status")
        yield Static("", classes="tool-output", id="tool-output")

    def on_mount(self) -> None:
        """Initialize display on mount."""
        self._update_display()

    def show_tool_running(self, name: str, args: dict) -> None:
        """Show a tool is currently running."""
        self.status = ToolStatus.RUNNING
        self.tool_name = name
        self.tool_args = args
        self.exit_code = None
        self._start_time = time.time()
        self._result = None
        self._update_display()

    def show_tool_result(self, result: str, exit_code: int | None = None) -> None:
        """Show tool execution result."""
        self.exit_code = exit_code
        self._result = result

        if exit_code is not None and exit_code != 0:
            self.status = ToolStatus.ERROR
        else:
            self.status = ToolStatus.COMPLETE

        self._update_display()

    def reset(self) -> None:
        """Reset to idle state."""
        self.status = ToolStatus.IDLE
        self.tool_name = None
        self.tool_args = None
        self.exit_code = None
        self._start_time = None
        self._result = None
        self._update_display()

    def _update_display(self) -> None:
        """Update the panel display."""
        try:
            status_widget = self.query_one("#tool-status", Static)
            output_widget = self.query_one("#tool-output", Static)
        except Exception:
            return  # Not mounted yet

        if self.status == ToolStatus.IDLE:
            status_widget.update(Panel(
                "No tool running",
                title="Tool Status",
                border_style="dim",
            ))
            output_widget.update("")

        elif self.status == ToolStatus.RUNNING:
            elapsed = time.time() - self._start_time if self._start_time else 0
            status_text = Text()
            status_text.append(f"● {self.tool_name}\n", style="yellow bold")

            if self.tool_args:
                for key, value in self.tool_args.items():
                    val_str = str(value)[:50]
                    if len(str(value)) > 50:
                        val_str += "..."
                    status_text.append(f"  {key}: {val_str}\n", style="dim")

            status_text.append(f"  elapsed: {elapsed:.1f}s\n", style="dim")
            status_text.append("  status: running...", style="yellow")

            status_widget.update(Panel(
                status_text,
                title="Tool Status",
                border_style="yellow",
            ))

        elif self.status == ToolStatus.COMPLETE:
            status_text = Text()
            status_text.append(f"✓ {self.tool_name}\n", style="green bold")
            if self.exit_code is not None:
                status_text.append(f"  exit code: {self.exit_code}", style="green")

            status_widget.update(Panel(
                status_text,
                title="Tool Status",
                border_style="green",
            ))

            if self._result:
                output_widget.update(Panel(
                    self._result[:500] + ("..." if len(self._result) > 500 else ""),
                    title="Output Preview",
                    border_style="dim",
                ))

        elif self.status == ToolStatus.ERROR:
            status_text = Text()
            status_text.append(f"✗ {self.tool_name}\n", style="red bold")
            if self.exit_code is not None:
                status_text.append(f"  exit code: {self.exit_code}", style="red")

            status_widget.update(Panel(
                status_text,
                title="Tool Status",
                border_style="red",
            ))

            if self._result:
                output_widget.update(Panel(
                    self._result[:500] + ("..." if len(self._result) > 500 else ""),
                    title="Error Output",
                    border_style="red",
                ))
