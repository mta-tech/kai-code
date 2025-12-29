"""Token usage indicator component for Rich UI.

Provides visual feedback on token usage with color-coded warnings
when approaching context limits.
"""

from rich.text import Text

from kai_code.cli_ui import TokenTracker


# Color scheme for token usage levels
# These match the colors in rich_config.COLORS but are specific to token status
TOKEN_COLORS = {
    "normal": "#10b981",  # Green - safe, plenty of context remaining
    "warning": "#fbbf24",  # Yellow - approaching limit (80-95%)
    "critical": "#ef4444",  # Red - near limit (>95%)
    "unknown": "#6b7280",  # Dim gray - no limit set
}


class TokenUsageIndicator:
    """Display token usage with color-coded status.

    The indicator shows token usage in a compact format and uses colors
    to indicate the status level:
    - Green (normal): < 80% of context limit
    - Yellow (warning): 80-95% of context limit
    - Red (critical): >= 95% of context limit
    - Gray (unknown): No context limit set
    """

    def __init__(self, token_tracker: TokenTracker) -> None:
        """Initialize the token usage indicator.

        Args:
            token_tracker: TokenTracker instance to display usage from
        """
        self._tracker = token_tracker

    @property
    def tracker(self) -> TokenTracker:
        """Get the underlying token tracker."""
        return self._tracker

    def render(self) -> Text:
        """Render the token usage indicator as a Rich Text object.

        Returns:
            Rich Text object with color-coded token usage display
        """
        # Get the compact display string from the tracker
        display = self._tracker.format_compact_display()

        # Determine the color based on status level
        status = self._tracker.get_status_level()
        color = TOKEN_COLORS.get(status, TOKEN_COLORS["unknown"])

        # Create the styled text
        text = Text()
        text.append(display, style=color)

        return text

    def render_with_label(self, label: str = "Tokens") -> Text:
        """Render the indicator with a prefix label.

        Args:
            label: The label to display before the token count

        Returns:
            Rich Text object with label and color-coded token usage
        """
        text = Text()
        text.append(f"{label}: ", style="bold")
        text.append_text(self.render())
        return text
