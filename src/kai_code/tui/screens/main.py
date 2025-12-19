"""Main chat screen for TUI."""

from textual.screen import Screen
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.binding import Binding

from ..widgets import (
    StatusBar,
    MessageList,
    ToolPanel,
    InputArea,
    InputSubmitted,
)
from ..components.message import MessageRole


class MainScreen(Screen):
    """Main chat screen with split layout."""

    DEFAULT_CSS = """
    MainScreen {
        layout: vertical;
    }

    MainScreen .main-content {
        height: 1fr;
    }

    MainScreen .message-area {
        width: 65%;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit", show=False),
        Binding("ctrl+c", "interrupt", "Interrupt", show=False),
        Binding("j", "scroll_down", "Scroll down", show=False),
        Binding("k", "scroll_up", "Scroll up", show=False),
    ]

    def __init__(
        self,
        model: str = "default",
        session: str = "default",
        yolo: bool = False,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self._model = model
        self._session = session
        self._yolo = yolo

    def compose(self) -> ComposeResult:
        yield StatusBar(
            model=self._model,
            session=self._session,
            yolo=self._yolo,
            id="status-bar",
        )
        with Horizontal(classes="main-content"):
            with Vertical(classes="message-area"):
                yield MessageList(id="message-list")
            yield ToolPanel(id="tool-panel")
        yield InputArea(id="input-area")

    def on_input_submitted(self, event: InputSubmitted) -> None:
        """Handle input submission."""
        # Will be handled by app
        pass

    def action_scroll_down(self) -> None:
        """Scroll message list down."""
        message_list = self.query_one("#message-list", MessageList)
        message_list.scroll_down()

    def action_scroll_up(self) -> None:
        """Scroll message list up."""
        message_list = self.query_one("#message-list", MessageList)
        message_list.scroll_up()

    def action_interrupt(self) -> None:
        """Interrupt current operation."""
        # Will be handled by app
        pass

    def action_quit(self) -> None:
        """Quit the application."""
        self.app.exit()
