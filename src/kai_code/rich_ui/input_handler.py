"""Input handling using Prompt Toolkit."""

import logging
from typing import Optional, Callable, List
from prompt_toolkit import prompt
from prompt_toolkit.history import FileHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.formatted_text import HTML
from pathlib import Path

logger = logging.getLogger("kai_code.rich_ui")


class RichInputHandler:
    """Handles user input using Prompt Toolkit."""
    
    def __init__(self, history_file: Optional[Path] = None):
        self.history_file = history_file or Path.home() / ".kai-code-history"
        self.history = FileHistory(str(self.history_file))
        self.commands = {
            "help": self._cmd_help,
            "quit": self._cmd_quit,
            "exit": self._cmd_quit,
            "clear": self._cmd_clear,
            "status": self._cmd_status,
        }
        
        # Setup key bindings
        self.key_bindings = KeyBindings()
        
        @self.key_bindings.add("c-c")
        def _(event):
            """Handle Ctrl+C to interrupt."""
            event.app.exit(exception=KeyboardInterrupt())
        
        @self.key_bindings.add("c-d")
        def _(event):
            """Handle Ctrl+D to quit."""
            event.app.exit(exception=EOFError())
    
    def get_input(self, prompt_text: str = "> ") -> str:
        """Get user input with prompt toolkit."""
        try:
            return prompt(
                HTML(f"<b>{prompt_text}</b>"),
                history=self.history,
                auto_suggest=AutoSuggestFromHistory(),
                key_bindings=self.key_bindings,
                multiline=False,
            )
        except (KeyboardInterrupt, EOFError):
            raise
    
    def is_slash_command(self, text: str) -> bool:
        """Check if text is a slash command."""
        return text.strip().startswith("/")
    
    def parse_command(self, text: str) -> tuple[str, str]:
        """Parse a slash command into (command, args)."""
        text = text.strip()
        if not text.startswith("/"):
            return ("", text)
        
        text = text[1:]  # Remove leading /
        parts = text.split(None, 1)
        
        if len(parts) == 0:
            return ("", "")
        elif len(parts) == 1:
            return (parts[0], "")
        else:
            return (parts[0], parts[1])
    
    def execute_command(self, command: str, args: str, context: dict) -> bool:
        """Execute a slash command. Returns True if should exit."""
        if command in self.commands:
            return self.commands[command](args, context)
        else:
            context["print_error"](f"Unknown command: /{command}")
            return False
    
    def _cmd_help(self, args: str, context: dict) -> bool:
        """Show help information."""
        help_text = """
Available commands:
  /help          Show this help message
  /quit, /exit   Exit the application
  /clear         Clear the message history
  /status        Show current status information
  
Any other input will be sent to the AI agent.
        """
        context["print_info"](help_text)
        return False
    
    def _cmd_quit(self, args: str, context: dict) -> bool:
        """Quit the application."""
        context["print_info"]("Goodbye!")
        return True
    
    def _cmd_clear(self, args: str, context: dict) -> bool:
        """Clear message history."""
        context["clear_messages"]()
        context["print_info"]("Messages cleared")
        return False
    
    def _cmd_status(self, args: str, context: dict) -> bool:
        """Show status information."""
        agent = context.get("agent")
        if agent:
            context["print_info"](
                f"Model: {getattr(agent, 'model', 'Unknown')}\n"
                f"Session: {getattr(agent, 'session', 'Unknown')}\n"
                f"YOLO Mode: {getattr(agent, 'yolo', False)}"
            )
        else:
            context["print_info"]("No active agent")
        return False
