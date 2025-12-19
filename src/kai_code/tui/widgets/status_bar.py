"""Status bar widget for kai-code TUI."""

from textual.widgets import Static
from textual.app import ComposeResult


class StatusBar(Static):
    """Top status bar showing model, session, and mode."""

    DEFAULT_CSS = """
    StatusBar {
        dock: top;
        height: 1;
        background: $primary;
        color: $text;
        padding: 0 1;
    }
    """

    def __init__(
        self,
        model: str = "default",
        session: str = "default",
        yolo: bool = False,
        tokens: int = 0,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self._model = model
        self._session = session
        self._yolo = yolo
        self._tokens = tokens

    def render_content(self) -> str:
        """Render the status bar content."""
        parts = [f"[kai-code]"]

        if self._yolo:
            parts.append("[YOLO]")

        parts.append(f"model: {self._model}")
        parts.append(f"session: {self._session}")

        if self._tokens > 0:
            if self._tokens >= 1000:
                parts.append(f"{self._tokens / 1000:.1f}k tok")
            else:
                parts.append(f"{self._tokens} tok")

        return " │ ".join(parts)

    def on_mount(self) -> None:
        """Update content on mount."""
        self.update(self.render_content())

    def set_model(self, model: str) -> None:
        """Update the model name."""
        self._model = model
        self.update(self.render_content())

    def set_session(self, session: str) -> None:
        """Update the session name."""
        self._session = session
        self.update(self.render_content())

    def set_yolo(self, yolo: bool) -> None:
        """Update YOLO mode."""
        self._yolo = yolo
        self.update(self.render_content())

    def set_tokens(self, tokens: int) -> None:
        """Update token count."""
        self._tokens = tokens
        self.update(self.render_content())
