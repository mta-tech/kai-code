"""Tool status display component for Rich UI."""

import logging
from typing import Optional
from rich.text import Text
from rich.panel import Panel
from rich.spinner import Spinner
from rich.progress import Progress, BarColumn, TextColumn, SpinnerColumn

logger = logging.getLogger("kai_code.rich_ui")


class ToolDisplay:
    """Handles tool status display."""
    
    def __init__(self):
        self.current_tool: Optional[str] = None
        self.tool_status = "idle"
        self.tool_details = ""
        self.progress_value = 0.0
    
    def start_tool(self, tool_name: str, details: str = ""):
        """Mark a tool as running."""
        self.current_tool = tool_name
        self.tool_status = "running"
        self.tool_details = details
        self.progress_value = 0.0
        logger.debug(f"Tool started: {tool_name}")
    
    def complete_tool(self, success: bool = True, details: str = ""):
        """Mark current tool as completed."""
        if self.current_tool:
            self.tool_status = "completed" if success else "error"
            self.tool_details = details
            self.progress_value = 1.0
            logger.debug(f"Tool completed: {self.current_tool}, success: {success}")
    
    def update_progress(self, value: float, details: str = ""):
        """Update tool progress."""
        self.progress_value = max(0.0, min(1.0, value))
        if details:
            self.tool_details = details
    
    def clear_tool(self):
        """Clear current tool status."""
        self.current_tool = None
        self.tool_status = "idle"
        self.tool_details = ""
        self.progress_value = 0.0
    
    def render(self) -> Panel:
        """Render tool status panel."""
        if self.tool_status == "idle":
            content = "[dim blue]No tool running[/dim blue]"
            border_style = "blue"
        elif self.tool_status == "running":
            content = self._render_running_tool()
            border_style = "yellow"
        elif self.tool_status == "completed":
            content = self._render_completed_tool()
            border_style = "green"
        elif self.tool_status == "error":
            content = self._render_error_tool()
            border_style = "red"
        else:
            content = "[dim]Unknown tool status[/dim]"
            border_style = "white"
        
        return Panel(
            content,
            title="Tool Status",
            border_style=border_style,
            padding=(1, 1)
        )
    
    def _render_running_tool(self) -> str:
        """Render running tool with spinner."""
        text = Text()
        
        # Tool name with spinner
        text.append("🔄 ", style="yellow")
        text.append(f"{self.current_tool or 'Unknown Tool'}\n", style="bold yellow")
        
        # Progress bar if applicable
        if self.progress_value > 0:
            text.append(f"Progress: {self.progress_value:.0%}\n", style="cyan")
        
        # Details
        if self.tool_details:
            text.append(f"{self.tool_details}", style="white")
        
        return text
    
    def _render_completed_tool(self) -> str:
        """Render completed tool."""
        text = Text()
        
        text.append("✅ ", style="green")
        text.append(f"{self.current_tool or 'Tool'} completed\n", style="bold green")
        
        if self.tool_details:
            text.append(f"{self.tool_details}", style="white")
        
        return text
    
    def _render_error_tool(self) -> str:
        """Render tool with error."""
        text = Text()
        
        text.append("❌ ", style="red")
        text.append(f"{self.current_tool or 'Tool'} failed\n", style="bold red")
        
        if self.tool_details:
            text.append(f"Error: {self.tool_details}", style="red")
        
        return text
