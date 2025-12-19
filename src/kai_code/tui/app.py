"""Main TUI application."""

from pathlib import Path

from textual.app import App
from textual.binding import Binding
from langgraph.types import Interrupt

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


# Tools that require approval when not in YOLO mode
SENSITIVE_TOOLS = {"execute", "write_file", "edit_file", "apply_patch"}


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

    def _needs_approval(self, tool_name: str) -> bool:
        """Check if a tool needs user approval."""
        if self._yolo:
            return False  # YOLO mode bypasses approval
        return tool_name in SENSITIVE_TOOLS

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
                # Check if this chunk is an interrupt (HITL approval required)
                if isinstance(chunk, tuple) and len(chunk) == 2:
                    # LangGraph streams tuples of (node_name, state)
                    node_name, state = chunk

                    # Check if there's an interrupt in the state
                    if isinstance(state, dict):
                        interrupts = state.get("__interrupts__", [])
                        if interrupts and not self._yolo:
                            # Handle the interrupt - show approval modal
                            for interrupt in interrupts:
                                if isinstance(interrupt, Interrupt):
                                    # Extract tool information from interrupt value
                                    tool_info = interrupt.value
                                    if isinstance(tool_info, dict):
                                        tool_name = tool_info.get("name", "unknown")
                                        tool_args = tool_info.get("args", {})

                                        if self._needs_approval(tool_name):
                                            # Show the tool in the tool panel
                                            tool_panel.show_tool_running(tool_name, tool_args)

                                            # Show approval modal and wait for decision
                                            result = await self.push_screen_wait(ApprovalModal(
                                                tool_name=tool_name,
                                                tool_args=tool_args,
                                            ))

                                            if result.decision == ApprovalDecision.REJECT:
                                                # User rejected the tool call
                                                streaming_msg.append_content(
                                                    f"\n\n[Tool '{tool_name}' was rejected by user]"
                                                )
                                                tool_panel.reset()
                                                return
                                            elif result.decision == ApprovalDecision.APPROVE:
                                                # User approved - resume the agent
                                                try:
                                                    # Resume with approval decision
                                                    for resume_chunk in self._agent._graph.stream(
                                                        None,
                                                        config={
                                                            "configurable": {"thread_id": self._agent.thread_id},
                                                        },
                                                    ):
                                                        # Continue processing resumed chunks
                                                        self._process_chunk(resume_chunk, streaming_msg)
                                                except Exception as e:
                                                    message_list.add_message(MessageRole.ERROR, f"Error resuming: {e}")
                                            # TODO: Handle EDIT decision

                # Process normal chunks (content updates)
                self._process_chunk(chunk, streaming_msg)

        except Exception as e:
            message_list.add_message(MessageRole.ERROR, f"Error: {e}")
        finally:
            self._streaming = False
            message_list.finish_streaming()
            tool_panel.reset()

    def _process_chunk(self, chunk: any, streaming_msg: any) -> None:
        """Process a stream chunk and update the streaming message."""
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
        elif isinstance(chunk, tuple) and len(chunk) == 2:
            # Handle tuple chunks (node_name, state)
            node_name, state = chunk
            if isinstance(state, dict) and isinstance(state.get("messages"), list):
                messages = state.get("messages", [])
                if messages:
                    last_msg = messages[-1]
                    if isinstance(last_msg, dict):
                        content = last_msg.get("content", "")
                    else:
                        content = getattr(last_msg, "content", "")

                    if content and isinstance(content, str):
                        streaming_msg._content = content
                        streaming_msg._refresh_display()

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

        # Note: The agent was initialized with the original yolo setting.
        # Toggling YOLO mode here affects only the TUI behavior (whether to show approval modals).
        # The agent's internal yolo setting and interrupt configuration remain unchanged.
        # To fully apply the new yolo mode to the agent, we would need to reinitialize it.

        message_list.add_message(
            MessageRole.ASSISTANT,
            f"YOLO mode {mode}. Note: Agent interrupt behavior set at startup.",
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
