"""Rich message display components.

Ported from letta-code with enhancements for kai-code.
"""

from __future__ import annotations

import logging
from typing import Optional, Any
from rich.text import Text
from rich.panel import Panel
from rich.console import Console, ConsoleOptions, RenderableType, RenderResult
from rich.layout import Layout
from rich.table import Table
from rich.align import Align
from rich.markdown import Markdown

from ..message_formatter import MessageFormatter

logger = logging.getLogger("kai_code.rich_ui")


class MessageDisplay:
    """Rich message display with two-column layout similar to letta-code."""
    
    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()
        self.formatter = MessageFormatter(console)
        
    def render_user_message(self, text: str, width: int = 80) -> Panel:
        """Render user message with '>' indicator in two-column layout."""
        content_width = max(0, width - 2)
        
        return Panel(
            self.formatter.format_markdown(text, content_width),
            title=f"[bold blue]> [/bold blue] User",
            border_style="blue",
            padding=(0, 1)
        )
    
    def render_assistant_message(self, text: str, streaming: bool = False, width: int = 80) -> Panel:
        """Render assistant message with bullet indicator in two-column layout."""
        content_width = max(0, width - 2)
        
        # Add streaming indicator
        title = "[bold green]●[/bold green] Assistant"
        if streaming:
            title += " [dim](streaming)[/dim]"
            
        return Panel(
            self.formatter.format_markdown(text, content_width),
            title=title,
            border_style="green",
            padding=(0, 1)
        )
    
    def render_tool_call(self, tool_name: str, args: dict, phase: str = "ready", width: int = 80) -> Panel:
        """Render tool call with status indicator."""
        # Determine status color and symbol
        status_config = {
            "streaming": ("●", "yellow", "streaming"),
            "ready": ("◉", "cyan", "pending"),
            "running": ("◉", "blue", "running"), 
            "finished": ("✓", "green", "completed")
        }
        
        symbol, color, status_text = status_config.get(phase, ("?", "red", "unknown"))
        
        title = f"[bold {color}]{symbol}[/bold {color}] {tool_name} [{color}]{status_text}[/{color}]"
        
        # Format arguments
        args_text = "\n".join([f"  {k}: {v}" for k, v in args.items()])
        
        return Panel(
            self.formatter.format_code(args_text, "json", width),
            title=title,
            border_style=color,
            padding=(0, 1)
        )
    
    def render_tool_result(self, tool_name: str, result: str, success: bool = True, width: int = 80) -> Panel:
        """Render tool result with status."""
        color = "green" if success else "red"
        symbol = "✓" if success else "✗"
        
        title = f"[bold {color}]{symbol}[/bold {color}] {tool_name} Result"
        
        return Panel(
            self.formatter.format_text(result, width),
            title=title,
            border_style=color,
            padding=(0, 1)
        )
    
    def render_error(self, text: str, title: str = "Error", width: int = 80) -> Panel:
        """Render error message."""
        return Panel(
            self.formatter.format_text(text, width),
            title=f"[bold red]✗[/bold red] {title}",
            border_style="red",
            padding=(0, 1)
        )
    
    def render_status(self, text: str, width: int = 80) -> Panel:
        """Render status message."""
        return Panel(
            self.formatter.format_text(text, width),
            title="[bold dim]ⓘ[/bold dim] Status",
            border_style="dim",
            padding=(0, 1)
        )
    
    def render_reasoning(self, text: str, streaming: bool = False, width: int = 80) -> Panel:
        """Render reasoning message."""
        title = "[bold magenta]🧠[/bold magenta] Reasoning"
        if streaming:
            title += " [dim](thinking)[/dim]"
            
        return Panel(
            self.formatter.format_markdown(text, width),
            title=title,
            border_style="magenta",
            padding=(0, 1)
        )
    
    def create_two_column_layout(self, left_column: str, right_content: RenderableType, width: int = 80) -> RenderableType:
        """Create two-column layout similar to letta-code."""
        layout = Layout()
        
        # Left column (2 chars wide)
        layout.split_column(
            Layout(name="left", size=2),
            Layout(name="right", ratio=1)
        )
        
        layout["left"].update(Text(left_column, justify="center"))
        layout["right"].update(right_content)
        
        return layout
    
    def render_conversation_history(self, messages: list[dict], width: int = 80) -> list[Panel]:
        """Render conversation history into list of panels."""
        panels = []
        
        for message in messages:
            msg_type = message.get("type", "unknown")
            
            if msg_type == "user":
                panels.append(self.render_user_message(message.get("text", ""), width))
            elif msg_type == "assistant":
                panels.append(self.render_assistant_message(
                    message.get("text", ""), 
                    message.get("streaming", False),
                    width
                ))
            elif msg_type == "tool_call":
                panels.append(self.render_tool_call(
                    message.get("tool_name", ""),
                    message.get("args", {}),
                    message.get("phase", "ready"),
                    width
                ))
            elif msg_type == "tool_result":
                panels.append(self.render_tool_result(
                    message.get("tool_name", ""),
                    message.get("result", ""),
                    message.get("success", True),
                    width
                ))
            elif msg_type == "error":
                panels.append(self.render_error(
                    message.get("text", ""),
                    message.get("title", "Error"),
                    width
                ))
            elif msg_type == "reasoning":
                panels.append(self.render_reasoning(
                    message.get("text", ""),
                    message.get("streaming", False),
                    width
                ))
            elif msg_type == "status":
                panels.append(self.render_status(message.get("text", ""), width))
                
        return panels
    
    def clear_messages(self) -> None:
        """Clear all messages (for compatibility)."""
        pass
    
    def render(self) -> RenderableType:
        """Render all current messages."""
        if not hasattr(self, 'current_messages') or not self.current_messages:
            return Text("No messages yet")
        
        # Return the last message panel for now
        last_msg = self.current_messages[-1]
        if last_msg and 'panel' in last_msg:
            return last_msg['panel']
        
        return Text("No messages to display")
