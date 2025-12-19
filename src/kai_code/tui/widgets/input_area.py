"""Input area widget for TUI."""

from textual.widgets import Input
from textual.message import Message


class InputSubmitted(Message):
    """Message sent when input is submitted."""

    def __init__(self, value: str, is_command: bool = False) -> None:
        super().__init__()
        self.value = value
        self.is_command = is_command


class InputArea(Input):
    """Input area with slash command support."""

    DEFAULT_CSS = """
    InputArea {
        dock: bottom;
        height: 3;
        border: solid $primary;
        padding: 0 1;
    }

    InputArea:focus {
        border: solid $accent;
    }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(
            placeholder="Type a message... (/help for commands)",
            **kwargs,
        )

    def is_slash_command(self, text: str) -> bool:
        """Check if text is a slash command."""
        return text.strip().startswith("/")

    def parse_slash_command(self, text: str) -> tuple[str, str]:
        """Parse a slash command into (command, args)."""
        text = text.strip()
        if not text.startswith("/"):
            return ("", text)

        text = text[1:]  # Remove leading /
        parts = text.split(None, 1)

        if len(parts) == 0:
            return ("", "")
        elif len(parts) == 1:
            return (parts[0], "")
        else:
            return (parts[0], parts[1])

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle input submission."""
        value = event.value.strip()
        if not value:
            return

        is_command = self.is_slash_command(value)
        self.clear()

        self.post_message(InputSubmitted(value, is_command))
