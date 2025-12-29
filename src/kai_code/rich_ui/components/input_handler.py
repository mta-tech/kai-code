"""Rich input handler with streaming state and commands.

Ported from letta-code with enhanced command support for kai-code.
"""

from __future__ import annotations

import logging
import shlex
from typing import Optional, Dict, Any, List, Tuple, Callable
from rich.text import Text
from rich.prompt import Prompt
from rich.console import Console
from rich.live import Live
from rich.spinner import Spinner
from rich.status import Status

from ..message_formatter import MessageFormatter

logger = logging.getLogger("kai_code.rich_ui")


class RichInputHandler:
    """Rich input handler with streaming state and command support."""
    
    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()
        self.formatter = MessageFormatter(console)
        
        # Command registry
        self.commands: Dict[str, Callable] = {
            "help": self._cmd_help,
            "quit": self._cmd_quit,
            "exit": self._cmd_quit,
            "clear": self._cmd_clear,
            "skills": self._cmd_skills,
            "load": self._cmd_load_skill,
            "unload": self._cmd_unload_skill,
            "list": self._cmd_list_skills,
            "resume": self._cmd_resume,
            "status": self._cmd_status,
            "history": self._cmd_history,
        }
        
        # State
        self.streaming = False
        self.current_command = None
        self.interrupt_requested = False
        
        # History
        self.command_history: List[str] = []
        self.max_history = 100
    
    def get_input(self, prompt: str = "kai> ", streaming: bool = False) -> str:
        """Get user input with streaming indicator."""
        self.streaming = streaming
        
        if streaming:
            return self._get_streaming_input(prompt)
        else:
            return self._get_normal_input(prompt)
    
    def _get_normal_input(self, prompt: str) -> str:
        """Get normal user input."""
        try:
            user_input = Prompt.ask(prompt, console=self.console).strip()
            
            if user_input:
                self.command_history.append(user_input)
                if len(self.command_history) > self.max_history:
                    self.command_history.pop(0)
            
            return user_input
            
        except (KeyboardInterrupt, EOFError):
            raise
    
    def _get_streaming_input(self, prompt: str) -> str:
        """Get input with streaming indicator."""
        # Show streaming indicator
        with Live(
            Text(f"[bold yellow]●[/bold yellow] [dim]Processing response...[/dim]"),
            console=self.console,
            refresh_per_second=1,
            transient=True
        ):
            try:
                user_input = Prompt.ask(
                    f"[dim]{prompt} (interrupt with Ctrl+C)[/dim]",
                    console=self.console
                ).strip()
                
                if user_input:
                    self.command_history.append(user_input)
                    if len(self.command_history) > self.max_history:
                        self.command_history.pop(0)
                
                return user_input
                
            except (KeyboardInterrupt, EOFError):
                self.interrupt_requested = True
                return ""
    
    def is_slash_command(self, input_text: str) -> bool:
        """Check if input is a slash command."""
        return input_text.startswith("/") and len(input_text) > 1
    
    def parse_command(self, input_text: str) -> Tuple[str, str]:
        """Parse command and arguments."""
        if not self.is_slash_command(input_text):
            return "", input_text
        
        # Remove leading slash
        cmd_text = input_text[1:].strip()
        
        # Parse command and args
        if " " in cmd_text:
            parts = cmd_text.split(" ", 1)
            command = parts[0]
            args = parts[1].strip()
        else:
            command = cmd_text
            args = ""
        
        return command, args
    
    def execute_command(self, command: str, args: str, context: Dict[str, Any]) -> bool:
        """Execute a command and return whether to exit."""
        if command not in self.commands:
            self.console.print(f"[red]Unknown command: {command}[/red]")
            self._cmd_help("")
            return False
        
        try:
            # Update context
            command_context = {**context, "args": args, "command": command}
            return self.commands[command](args, command_context)
        except Exception as e:
            logger.error(f"Error executing command {command}: {e}")
            self.console.print(f"[red]Error: {e}[/red]")
            return False
    
    def render_thinking_indicator(self, message: str) -> Text:
        """Render thinking indicator."""
        return Text(f"[bold magenta]🧠[/bold magenta] [dim]{message}[/dim]")
    
    def render_input_status(self, message: str) -> Status:
        """Render input status."""
        return Status(f"[bold blue]●[/bold blue] {message}", spinner="dots")
    
    # Command implementations
    
    def _cmd_help(self, args: str, context: Dict[str, Any]) -> bool:
        """Show help information."""
        help_table = self.formatter.create_help_table(self.commands.keys(), [
            "help", "quit", "exit", "clear", "skills", "load", "unload", 
            "list", "resume", "status", "history"
        ])
        
        self.console.print(Panel(help_table, title="[bold]Available Commands[/bold]", border_style="blue"))
        return False
    
    def _cmd_quit(self, args: str, context: Dict[str, Any]) -> bool:
        """Quit application."""
        self.console.print("[green]Goodbye![/green]")
        return True
    
    def _cmd_clear(self, args: str, context: Dict[str, Any]) -> bool:
        """Clear screen."""
        self.console.clear()
        return False
    
    def _cmd_skills(self, args: str, context: Dict[str, Any]) -> bool:
        """Show skills information."""
        agent = context.get("agent")
        if not agent:
            self.console.print("[red]No agent available[/red]")
            return False
            
        memory_manager = getattr(agent, '_memory_manager', None)
        if not memory_manager:
            self.console.print("[red]No memory manager available[/red]")
            return False
            
        # Get skills information
        skills_block = memory_manager.get_skills_block()
        loaded_block = memory_manager.get_loaded_skills_block()
        
        skills_info = []
        if skills_block and skills_block.skills:
            skills_info.extend([f"Available: {len(skills_block.skills)}"])
        if loaded_block:
            skills_info.extend([f"Loaded: {len(loaded_block.loaded_skills)}"])
        
        self.console.print(Panel(
            "\n".join(skills_info),
            title="[bold]Skills Status[/bold]",
            border_style="blue"
        ))
        return False
    
    def _cmd_load_skill(self, args: str, context: Dict[str, Any]) -> bool:
        """Load a skill."""
        if not args:
            self.console.print("[red]Usage: /load <skill_id>[/red]")
            return False
            
        agent = context.get("agent")
        if not agent:
            self.console.print("[red]No agent available[/red]")
            return False
            
        # This would integrate with skill tools
        self.console.print(f"[green]Loading skill: {args}[/green]")
        self.console.print("[dim]Use agent tools for actual skill loading[/dim]")
        return False
    
    def _cmd_unload_skill(self, args: str, context: Dict[str, Any]) -> bool:
        """Unload a skill."""
        if not args:
            self.console.print("[red]Usage: /unload <skill_id>[/red]")
            return False
            
        agent = context.get("agent")
        if not agent:
            self.console.print("[red]No agent available[/red]")
            return False
            
        self.console.print(f"[yellow]Unloading skill: {args}[/yellow]")
        self.console.print("[dim]Use agent tools for actual skill unloading[/dim]")
        return False
    
    def _cmd_list_skills(self, args: str, context: Dict[str, Any]) -> bool:
        """List available skills."""
        agent = context.get("agent")
        if not agent:
            self.console.print("[red]No agent available[/red]")
            return False
            
        memory_manager = getattr(agent, '_memory_manager', None)
        if not memory_manager:
            self.console.print("[red]No memory manager available[/red]")
            return False
            
        # List loaded skills
        loaded_skills = memory_manager.list_loaded_skills()
        if loaded_skills:
            skills_table = Table(title="Loaded Skills", box=None)
            skills_table.add_column("Skill ID", style="cyan")
            skills_table.add_column("Status", style="green")
            
            for skill_id in loaded_skills:
                skills_table.add_row(skill_id, "[green]✓ Loaded[/green]")
            
            self.console.print(Panel(skills_table, border_style="blue"))
        else:
            self.console.print("[yellow]No skills currently loaded[/yellow]")
            
        return False
    
    def _cmd_resume(self, args: str, context: Dict[str, Any]) -> bool:
        """Resume interrupted session."""
        self.console.print("[yellow]Session resume not yet implemented[/yellow]")
        return False
    
    def _cmd_status(self, args: str, context: Dict[str, Any]) -> bool:
        """Show current status."""
        agent = context.get("agent")
        
        status_info = []
        status_info.append(f"Streaming: {'Yes' if self.streaming else 'No'}")
        status_info.append(f"History Length: {len(self.command_history)}")
        
        if agent:
            model = getattr(agent, '_config', None)
            if model:
                status_info.append(f"Model: {model.model}")
                
            memory_manager = getattr(agent, '_memory_manager', None)
            if memory_manager:
                blocks = memory_manager.list_blocks()
                status_info.append(f"Memory Blocks: {len(blocks)}")
        
        self.console.print(Panel(
            "\n".join(status_info),
            title="[bold]Status[/bold]",
            border_style="blue"
        ))
        return False
    
    def _cmd_history(self, args: str, context: Dict[str, Any]) -> bool:
        """Show command history."""
        if not self.command_history:
            self.console.print("[yellow]No command history available[/yellow]")
            return False
        
        history_table = Table(title="Command History", box=None)
        history_table.add_column("#", style="dim", width=4)
        history_table.add_column("Command", style="white")
        
        for i, cmd in enumerate(self.command_history, 1):
            history_table.add_row(str(i), cmd)
        
        # Show last 20 commands
        panel_content = self._truncate_table_content(history_table, 20)
        self.console.print(Panel(panel_content, title="[bold]Recent Commands[/bold]", border_style="blue"))
        return False
    
    def _truncate_table_content(self, table, max_rows):
        """Create panel with truncated table content."""
        # Convert table to string lines and truncate
        lines = str(table).split("\n")
        if len(lines) > max_rows + 2:  # +2 for header/footer
            lines = lines[:max_rows + 2]  # Include table header
            lines.append(f"[dim]... and {len(lines) - max_rows - 2} more entries[/dim]")
        
        from rich.text import Text
        return Text("\n".join(lines))
