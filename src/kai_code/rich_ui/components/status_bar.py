"""Rich status bar component."""

from typing import Optional
from rich.text import Text
from rich.panel import Panel


class RichStatusBar:
    """Status bar for Rich UI."""
    
    def __init__(self, model: str = "default", session: str = "default", yolo: bool = False):
        self.model = model
        self.session = session
        self.yolo = yolo
    
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
            padding=(0, 1)
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
