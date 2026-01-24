"""Rich status bar component."""

from typing import TYPE_CHECKING

from rich.panel import Panel
from rich.text import Text

if TYPE_CHECKING:
    from kai_code.cli_ui import TokenTracker

from .token_indicator import TokenUsageIndicator


class RichStatusBar:
    """Status bar for Rich UI."""

    def __init__(
        self,
        model: str = "default",
        session: str = "default",
        yolo: bool = False,
        token_tracker: "TokenTracker | None" = None,
    ):
        self.model = model
        self.session = session
        self.yolo = yolo
        self._token_tracker = token_tracker
        self._token_indicator: TokenUsageIndicator | None = None
        if token_tracker is not None:
            self._token_indicator = TokenUsageIndicator(token_tracker)
    
    def render(self) -> Panel:
        """Render the status bar."""
        content = Text()

        # Model info
        content.append("Model: ", style="bold")
        content.append(f"{self.model} ", style="cyan")

        # Session info
        content.append("│ Session: ", style="bold")
        content.append(f"{self.session} ", style="blue")

        # YOLO mode
        yolo_status = "ON" if self.yolo else "OFF"
        yolo_style = "green" if self.yolo else "red"
        content.append("│ YOLO: ", style="bold")
        content.append(f"{yolo_status}", style=yolo_style)

        return Panel(
            content,
            title="[bold blue]Kai Code[/bold blue]",
            border_style="blue",
            padding=(0, 1),
        )
    
    def update_model(self, model: str):
        """Update the model name."""
        self.model = model
    
    def update_session(self, session: str):
        """Update the session name."""
        self.session = session
    
    def update_yolo(self, yolo: bool):
        """Update YOLO mode status."""
        self.yolo = yolo

    def set_token_tracker(self, token_tracker: "TokenTracker | None") -> None:
        """Set or update the token tracker.

        Args:
            token_tracker: TokenTracker instance for displaying usage, or None to disable
        """
        self._token_tracker = token_tracker
        if token_tracker is not None:
            self._token_indicator = TokenUsageIndicator(token_tracker)
        else:
            self._token_indicator = None

    @property
    def token_tracker(self) -> "TokenTracker | None":
        """Get the current token tracker."""
        return self._token_tracker

    def render_token_display(self) -> Text:
        """Render the token display for use in footer.

        Returns:
            Text object with token info, or empty Text if no token tracker
        """
        if self._token_indicator is not None:
            return self._token_indicator.render_with_label("Tokens")
        return Text()
