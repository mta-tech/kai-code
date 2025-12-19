"""Main TUI application."""

from textual.app import App, ComposeResult
from textual.widgets import Static


class KaiCodeApp(App):
    """kai-code interactive TUI application."""

    TITLE = "kai-code"

    def compose(self) -> ComposeResult:
        yield Static("kai-code TUI - Loading...")


def main() -> None:
    """Run the TUI application."""
    app = KaiCodeApp()
    app.run()


if __name__ == "__main__":
    main()
