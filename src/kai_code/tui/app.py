"""Main TUI application."""

from pathlib import Path

from textual.app import App
from textual.binding import Binding

from ..agent import KaiAgent
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
        self._init_agent()

    def _init_agent(self) -> None:
        """Initialize the agent."""
        try:
            self._agent = KaiAgent(
                root_dir=self.root_dir,
                model=self._model if self._model != "default" else None,
                yolo=self._yolo,
            )
        except Exception as e:
            # Agent initialization can fail if no API key is set
            self._agent = None

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

        # Run agent
        self.run_worker(self._run_agent_stream(text))

    async def _run_agent_stream(self, prompt: str) -> None:
        """Run agent and stream response to UI."""
        if not self._agent:
            message_list = self.query_one("#message-list", MessageList)
            message_list.add_message(
                MessageRole.ERROR,
                "No agent available. Check API key configuration.",
            )
            return

        message_list = self.query_one("#message-list", MessageList)
        tool_panel = self.query_one("#tool-panel", ToolPanel)

        self._streaming = True
        streaming_msg = message_list.add_streaming_message(MessageRole.ASSISTANT)

        try:
            # The agent.stream() returns an iterator of response chunks
            # We need to process these chunks and update the UI
            for chunk in self._agent.stream(prompt):
                # Extract content from chunk
                # The chunk is a dict with messages
                if isinstance(chunk, dict) and isinstance(chunk.get("messages"), list):
                    messages = chunk.get("messages", [])
                    if messages:
                        # Get the last message
                        last_msg = messages[-1]
                        # Extract content based on message type
                        if isinstance(last_msg, dict):
                            content = last_msg.get("content", "")
                        else:
                            # Handle LangChain BaseMessage
                            content = getattr(last_msg, "content", "")

                        # Update streaming message with full content
                        # (since we get full state each time)
                        if content and isinstance(content, str):
                            # Replace content instead of appending since we get full state
                            streaming_msg._content = content
                            streaming_msg._refresh_display()

        except Exception as e:
            message_list.add_message(MessageRole.ERROR, f"Error: {e}")
        finally:
            self._streaming = False
            message_list.finish_streaming()
            tool_panel.reset()

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
