"""Main TUI application."""

from pathlib import Path

from textual.app import App
from textual.binding import Binding

from .screens.main import MainScreen
from .widgets import (
    StatusBar,
    MessageList,
    ToolPanel,
    InputArea,
    InputSubmitted,
    ApprovalModal,
    ApprovalDecision,
    ApprovalResult,
)
from .components.message import MessageRole
from .commands import CommandRegistry


class KaiCodeApp(App):
    """kai-code interactive TUI application."""

    TITLE = "kai-code"

    CSS = """
    Screen {
        background: $background;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("ctrl+c", "interrupt", "Interrupt"),
    ]

    def __init__(
        self,
        root_dir: str | Path = ".",
        model: str = "default",
        session: str = "default",
        yolo: bool = True,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.root_dir = Path(root_dir).resolve()
        self._model = model
        self._session = session
        self._yolo = yolo
        self._commands = CommandRegistry()
        self._agent = None  # Will hold KaiAgent instance
        self._streaming = False

    def on_mount(self) -> None:
        """Set up the app on mount."""
        self.push_screen(MainScreen(
            model=self._model,
            session=self._session,
            yolo=self._yolo,
        ))

    def on_input_submitted(self, event: InputSubmitted) -> None:
        """Handle input from user."""
        if event.is_command:
            self._handle_command(event.value)
        else:
            self._handle_message(event.value)

    def _handle_command(self, text: str) -> None:
        """Handle a slash command."""
        # Parse command
        text = text.strip()
        if not text.startswith("/"):
            return

        parts = text[1:].split(None, 1)
        cmd_name = parts[0] if parts else ""
        cmd_args = parts[1] if len(parts) > 1 else ""

        if not self._commands.is_valid(cmd_name):
            self._show_error(f"Unknown command: /{cmd_name}")
            return

        # Execute command
        if cmd_name in ("exit", "quit", "q"):
            self.exit()
        elif cmd_name == "help":
            self._show_help()
        elif cmd_name == "clear":
            self._clear_messages()
        elif cmd_name == "yolo":
            self._toggle_yolo()
        elif cmd_name == "model":
            self._switch_model(cmd_args)
        elif cmd_name == "session":
            self._show_session_info()
        else:
            self._show_error(f"Command not yet implemented: /{cmd_name}")

    def _handle_message(self, text: str) -> None:
        """Handle a user message."""
        message_list = self.query_one("#message-list", MessageList)
        message_list.add_message(MessageRole.USER, text)

        # TODO: Send to agent and stream response
        # For now, just echo back
        message_list.add_message(
            MessageRole.ASSISTANT,
            f"[TUI Demo] You said: {text}\n\nAgent integration coming soon...",
        )

    def _show_help(self) -> None:
        """Show help text."""
        message_list = self.query_one("#message-list", MessageList)
        help_text = self._commands.get_help_text()
        message_list.add_message(MessageRole.ASSISTANT, help_text)

    def _show_error(self, error: str) -> None:
        """Show error message."""
        message_list = self.query_one("#message-list", MessageList)
        message_list.add_message(MessageRole.ERROR, error)

    def _clear_messages(self) -> None:
        """Clear all messages."""
        message_list = self.query_one("#message-list", MessageList)
        message_list.clear_messages()

    def _toggle_yolo(self) -> None:
        """Toggle YOLO mode."""
        self._yolo = not self._yolo
        status_bar = self.query_one("#status-bar", StatusBar)
        status_bar.set_yolo(self._yolo)

        message_list = self.query_one("#message-list", MessageList)
        mode = "enabled" if self._yolo else "disabled"
        message_list.add_message(
            MessageRole.ASSISTANT,
            f"YOLO mode {mode}.",
        )

    def _switch_model(self, model: str) -> None:
        """Switch to a different model."""
        if not model:
            self._show_error("Usage: /model <model-name>")
            return

        self._model = model
        status_bar = self.query_one("#status-bar", StatusBar)
        status_bar.set_model(model)

        message_list = self.query_one("#message-list", MessageList)
        message_list.add_message(
            MessageRole.ASSISTANT,
            f"Switched to model: {model}",
        )

    def _show_session_info(self) -> None:
        """Show current session info."""
        message_list = self.query_one("#message-list", MessageList)
        info = f"""Session Info:
- Root: {self.root_dir}
- Model: {self._model}
- Session: {self._session}
- YOLO: {self._yolo}"""
        message_list.add_message(MessageRole.ASSISTANT, info)

    def action_interrupt(self) -> None:
        """Interrupt current operation."""
        if self._streaming:
            # TODO: Cancel streaming
            pass
        else:
            self.exit()


def main() -> None:
    """Run the TUI application."""
    app = KaiCodeApp()
    app.run()


if __name__ == "__main__":
    main()
