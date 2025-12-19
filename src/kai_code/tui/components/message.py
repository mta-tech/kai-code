"""Message component for TUI."""

from enum import Enum
from textual.widgets import Static
from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text


class MessageRole(Enum):
    """Message role types."""
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"
    ERROR = "error"


class Message(Static):
    """A single message in the conversation."""

    ROLE_STYLES = {
        MessageRole.USER: ("User", "blue"),
        MessageRole.ASSISTANT: ("Assistant", "green"),
        MessageRole.TOOL: ("Tool", "yellow"),
        MessageRole.ERROR: ("Error", "red"),
    }

    def __init__(
        self,
        role: MessageRole,
        content: str = "",
        tool_name: str | None = None,
        streaming: bool = False,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.role = role
        self._content = content
        self.tool_name = tool_name
        self.streaming = streaming

    @property
    def content(self) -> str:
        """Get message content."""
        return self._content

    def append_content(self, text: str) -> None:
        """Append content during streaming."""
        self._content += text
        self._refresh_display()

    def finish_streaming(self) -> None:
        """Mark streaming as complete."""
        self.streaming = False
        self._refresh_display()

    def _refresh_display(self) -> None:
        """Update the display."""
        self.update(self._render())

    def _render(self) -> Panel:
        """Render the message as a Rich Panel."""
        title, color = self.ROLE_STYLES.get(
            self.role, ("Message", "white")
        )

        if self.role == MessageRole.TOOL and self.tool_name:
            title = f"Tool: {self.tool_name}"

        content = self._content
        if self.streaming:
            content += " █"  # Cursor indicator

        # Try to render as markdown for assistant messages
        if self.role == MessageRole.ASSISTANT and not self.streaming:
            try:
                renderable = Markdown(content)
            except Exception:
                renderable = Text(content)
        else:
            renderable = Text(content)

        return Panel(
            renderable,
            title=title,
            border_style=color,
            expand=True,
        )

    def on_mount(self) -> None:
        """Render on mount."""
        self.update(self._render())
