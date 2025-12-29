"""Rich console management for the UI."""

import logging
from typing import Optional
from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.live import Live
from rich.status import Status

logger = logging.getLogger("kai_code.rich_ui")


class RichConsoleManager:
    """Manages Rich console and layout for the interactive UI."""
    
    def __init__(self):
        self.console = Console()
        self.layout = Layout()
        self.live: Optional[Live] = None
        self.setup_layout()
    
    def setup_layout(self):
        """Set up the console layout."""
        self.layout.split(
            Layout(name="header", size=3),
            Layout(name="main", ratio=1),
            Layout(name="footer", size=3)
        )
        
        self.layout["main"].split_row(
            Layout(name="messages", ratio=2),
            Layout(name="tools", size=40)
        )
    
    def start_live_display(self):
        """Start the live display."""
        if self.live is None:
            self.live = Live(
                self.layout,
                console=self.console,
                refresh_per_second=4,
                auto_refresh=True
            )
            self.live.start()
    
    def stop_live_display(self):
        """Stop the live display."""
        if self.live:
            self.live.stop()
            self.live = None
    
    def update_header(self, content):
        """Update the header panel."""
        self.layout["header"].update(Panel(content, title="Kai Code"))
        if self.live:
            self.live.refresh()
    
    def update_messages(self, content):
        """Update the messages panel."""
        self.layout["messages"].update(Panel(content, title="Messages"))
        if self.live:
            self.live.refresh()
    
    def update_tools(self, content):
        """Update the tools panel."""
        self.layout["tools"].update(Panel(content, title="Tool Status"))
        if self.live:
            self.live.refresh()
    
    def update_footer(self, content):
        """Update the footer panel."""
        self.layout["footer"].update(Panel(content, title="Input"))
        if self.live:
            self.live.refresh()
    
    def print_error(self, message: str):
        """Print an error message outside the live display."""
        self.console.print(f"[red]Error: {message}[/red]")
    
    def print_info(self, message: str):
        """Print an info message outside the live display."""
        self.console.print(f"[blue]Info: {message}[/blue]")
    
    def print_success(self, message: str):
        """Print a success message outside the live display."""
        self.console.print(f"[green]✓ {message}[/green]")
    
    def show_status(self, message: str, spinner="dots"):
        """Show a temporary status message."""
        with Status(message, spinner=spinner, console=self.console):
            # This will be used by the caller to control when it finishes
            yield
