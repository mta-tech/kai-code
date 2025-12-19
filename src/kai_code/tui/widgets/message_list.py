"""Message list widget for TUI."""

from textual.widgets import Static
from textual.containers import VerticalScroll
from textual.app import ComposeResult

from ..components.message import Message, MessageRole


class MessageList(VerticalScroll):
    """Scrollable list of conversation messages."""

    DEFAULT_CSS = """
    MessageList {
        height: 1fr;
        padding: 1;
    }

    MessageList Message {
        margin-bottom: 1;
    }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._messages: list[Message] = []
        self._streaming_message: Message | None = None

    def on_mount(self) -> None:
        """Mount any pending messages when widget is mounted."""
        for msg in self._messages:
            if msg.parent is None:
                self.mount(msg)

    @property
    def message_count(self) -> int:
        """Get number of messages."""
        return len(self._messages)

    def add_message(
        self,
        role: MessageRole,
        content: str,
        tool_name: str | None = None,
    ) -> Message:
        """Add a complete message to the list."""
        msg = Message(role=role, content=content, tool_name=tool_name)
        self._messages.append(msg)
        if self.is_attached:
            self.mount(msg)
            self.scroll_end(animate=False)
        return msg

    def add_streaming_message(self, role: MessageRole) -> Message:
        """Add a new message that will receive streaming content."""
        msg = Message(role=role, content="", streaming=True)
        self._messages.append(msg)
        self._streaming_message = msg
        if self.is_attached:
            self.mount(msg)
            self.scroll_end(animate=False)
        return msg

    def get_streaming_message(self) -> Message | None:
        """Get the currently streaming message, if any."""
        return self._streaming_message

    def finish_streaming(self) -> None:
        """Mark current streaming message as complete."""
        if self._streaming_message:
            self._streaming_message.finish_streaming()
            self._streaming_message = None

    def clear_messages(self) -> None:
        """Remove all messages."""
        for msg in self._messages:
            if msg.is_attached:
                msg.remove()
        self._messages.clear()
        self._streaming_message = None
