"""Rich message formatter utilities.

Enhanced with letta-code markdown rendering capabilities.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Optional, List
from datetime import datetime
from rich.text import Text
from rich.panel import Panel
from rich.markdown import Markdown
from rich.syntax import Syntax
from rich.table import Table
from rich.console import Console, ConsoleOptions, RenderableType, RenderResult

logger = logging.getLogger("kai_code.rich_ui")


class MessageFormatter:
    """Formats messages for Rich display with letta-code style rendering."""
    
    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()
    
    def format_message(self, role: str, content: str, tool_name: Optional[str] = None) -> Panel:
        """Format a single message for display."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Determine style based on role
        if role.lower() == "user":
            title = f"[bold blue]You[/bold blue] - {timestamp}"
            style = "blue"
        elif role.lower() == "assistant":
            title = f"[bold green]Assistant[/bold green] - {timestamp}"
            style = "green"
        elif role.lower() == "system":
            title = f"[bold yellow]System[/bold yellow] - {timestamp}"
            style = "yellow"
        elif role.lower() == "tool":
            tool_display = tool_name or "Unknown Tool"
            title = f"[bold cyan]Tool: {tool_display}[/bold cyan] - {timestamp}"
            style = "cyan"
        else:
            title = f"[bold]Message[/bold] - {timestamp}"
            style = "white"
        
        # Format content based on type
        formatted_content = self._format_content(content, role)
        
        return Panel(
            formatted_content,
            title=title,
            border_style=style,
            padding=(0, 1)
        )
    
    def _format_content(self, content: str, role: str):
        """Format content based on role and content type."""
        if not content.strip():
            return Text("...")
        
        # Check if content is code
        if content.strip().startswith("```"):
            return self._format_code_block(content)
        
        # Check if content is JSON or structured data
        if content.strip().startswith("{") or content.strip().startswith("["):
            try:
                import json
                parsed = json.loads(content)
                return self._format_json(parsed)
            except:
                pass  # Fall back to markdown
        
        # Use markdown for most text content
        try:
            return Markdown(content)
        except Exception:
            # Fallback to plain text
            return Text(content)
    
    def _format_code_block(self, content: str):
        """Format a code block with syntax highlighting."""
        # Extract language and code
        lines = content.split("\n")
        if len(lines) < 2:
            return Text(content)
        
        first_line = lines[0].strip()
        if first_line.startswith("```"):
            language = first_line[3:].strip()
            code = "\n".join(lines[1:])
            if code.endswith("```"):
                code = code[:-3].rstrip()
        else:
            language = "text"
            code = content
        
        try:
            return Syntax(
                code,
                language,
                theme="monokai",
                line_numbers=False,
                word_wrap=True
            )
        except Exception:
            return Text(code)
    
    def _format_json(self, data):
        """Format JSON data nicely."""
        import json
        formatted_json = json.dumps(data, indent=2)
        return Syntax(
            formatted_json,
            "json",
            theme="monokai",
            line_numbers=False,
            word_wrap=True
        )
    
    def format_tool_status(self, tool_name: str, status: str, details: Optional[str] = None) -> Panel:
        """Format tool status display."""
        status_style = {
            "running": "yellow",
            "completed": "green", 
            "error": "red",
            "idle": "blue"
        }.get(status.lower(), "white")
        
        content = Text()
        content.append(f"Tool: ", style="bold")
        content.append(f"{tool_name}\n", style="cyan")
        content.append(f"Status: ", style="bold")
        content.append(f"{status}\n", style=status_style)
        
        if details:
            content.append(f"Details: ", style="bold")
            content.append(details, style="white")
        
        return Panel(
            content,
            title=f"[bold]Tool Status[/bold]",
            border_style=status_style,
            padding=(0, 1)
        )
    
    def format_approval_prompt(self, tool_name: str, action: str) -> Table:
        """Format an approval prompt for sensitive actions."""
        table = Table(title="Approval Required")
        table.add_column("Field", style="cyan")
        table.add_column("Value", style="white")
        
        table.add_row("Tool", tool_name)
        table.add_row("Action", action)
        table.add_row("Approve?", "[y]es / [n]o")
        
        return table
    
    def format_error(self, error_message: str) -> Panel:
        """Format an error message."""
        return Panel(
            Text(error_message, style="red"),
            title="[bold red]Error[/bold red]",
            border_style="red",
            padding=(0, 1)
        )
    
    def format_info(self, info_message: str) -> Panel:
        """Format an info message."""
        return Panel(
            Text(info_message, style="blue"),
            title="[bold blue]Info[/bold blue]",
            border_style="blue",
            padding=(0, 1)
        )
    
    def format_markdown(self, text: str, width: int = 80) -> RenderableType:
        """Format markdown text using letta-code style pure Rich rendering."""
        return self.render_markdown_display(text, width, hanging_indent=0)
    
    def render_markdown_display(self, text: str, width: int, hanging_indent: int = 0) -> RenderableType:
        """Render full markdown content using pure Rich components.
        
        Based on letta-code's approach - NO ANSI codes, pure Rich rendering.
        """
        if not text:
            return Text("")
        
        lines = text.split("\n")
        content_blocks: List[RenderableType] = []

        # Regex patterns for markdown elements (from letta-code)
        header_regex = re.compile(r'^(#{1,6})\s+(.*)$')
        code_block_regex = re.compile(r'^```(\w*)?$')
        list_item_regex = re.compile(r'^(\s*)([*\-+]|\d+\.)\s+(.*)$')
        blockquote_regex = re.compile(r'^>\s*(.*)$')
        hr_regex = re.compile(r'^[-*_]{3,}$')

        in_code_block = False
        code_block_content: List[str] = []
        code_block_lang = ""

        for index, line in enumerate(lines):
            # Handle code blocks
            if line.match(code_block_regex):
                if not in_code_block:
                    # Start of code block
                    match = line.match(code_block_regex)
                    code_block_lang = match and match[1] or ""
                    in_code_block = True
                    code_block_content = []
                else:
                    # End of code block
                    if code_block_content:
                        code_text = "\n".join(code_block_content)
                        syntax = Syntax(code_text, code_block_lang or "text", theme="monokai", line_numbers=False)
                        content_blocks.append(syntax)
                    in_code_block = False
                    code_block_content = []
                continue

            # Handle code block content
            if in_code_block:
                code_block_content.append(line)
                continue

            # Handle headers
            header_match = header_regex.match(line)
            if header_match:
                level = len(header_match[1])
                header_text = header_match[2]
                styles = ["bold", "yellow", "magenta", "cyan", "green", "blue"]
                style = styles[level - 1] if level <= len(styles) else "white"
                header_display = Text("#" * level + " " + header_text, style=style)
                content_blocks.append(header_display)
                continue

            # Handle list items
            list_match = list_item_regex.match(line)
            if list_match:
                indent = list_match[1]
                marker = list_match[2]
                content = list_match[3]
                list_display = Text(
                    " " * len(indent) + f"• " + content,
                    style="yellow" if marker.startswith(("*", "-", "+")) else "white"
                )
                content_blocks.append(list_display)
                continue

            # Handle blockquotes
            blockquote_match = blockquote_regex.match(line)
            if blockquote_match:
                quote_text = blockquote_match[1]
                quote_display = Text("❝ " + quote_text, style="cyan italic")
                content_blocks.append(quote_display)
                continue

            # Handle horizontal rules
            if hr_regex.match(line):
                hr_display = Text("─" * min(width, 20), style="dim")
                content_blocks.append(hr_display)
                continue

            # Regular text
            if line.strip():
                text_display = Text(line)
                content_blocks.append(text_display)
            else:
                # Empty line
                content_blocks.append(Text(""))

        return content_blocks if len(content_blocks) > 1 else (content_blocks[0] if content_blocks else Text(""))
    
    def format_code(self, code: str, language: str = "text", width: int = 80) -> RenderableType:
        """Format code block with syntax highlighting."""
        syntax = Syntax(code, language, theme="monokai", line_numbers=False)
        return syntax
    
    def create_help_table(self, commands: List[str], featured: List[str] = None) -> Table:
        """Create help table for commands."""
        table = Table(title="Available Commands", box=None)
        table.add_column("Command", style="cyan", width=15)
        table.add_column("Description", style="white")
        
        # Command descriptions
        descriptions = {
            "help": "Show this help message",
            "quit": "Exit the application",
            "exit": "Exit the application", 
            "clear": "Clear the screen",
            "skills": "Show skills information",
            "load": "Load a skill (usage: /load <skill_id>)",
            "unload": "Unload a skill (usage: /unload <skill_id>)",
            "list": "List loaded skills",
            "resume": "Resume interrupted session",
            "status": "Show current status",
            "history": "Show command history"
        }
        
        # Sort commands, featured first
        if featured:
            other_commands = [cmd for cmd in commands if cmd not in featured]
            sorted_commands = featured + other_commands
        else:
            sorted_commands = sorted(commands)
        
        for cmd in sorted_commands:
            desc = descriptions.get(cmd, "No description available")
            style = "bold green" if cmd in (featured or []) else "white"
            table.add_row(f"[{style}]{cmd}[/{style}]", desc)
        
        return table
    
    def normalize_text(self, text: str) -> str:
        """Normalize text similar to letta-code approach."""
        return text
