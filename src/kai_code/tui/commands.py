"""Slash command registry for TUI."""

from dataclasses import dataclass
from typing import Callable, Any


@dataclass
class Command:
    """A slash command definition."""
    name: str
    description: str
    aliases: list[str] | None = None
    requires_arg: bool = False


COMMANDS: dict[str, Command] = {
    "help": Command(
        name="help",
        description="Show available commands",
    ),
    "model": Command(
        name="model",
        description="Switch model (e.g., /model gpt-4o)",
        requires_arg=True,
    ),
    "clear": Command(
        name="clear",
        description="Clear conversation history",
    ),
    "exit": Command(
        name="exit",
        description="Exit TUI",
        aliases=["quit", "q"],
    ),
    "agent": Command(
        name="agent",
        description="Switch named agent (e.g., /agent myproject)",
        requires_arg=True,
    ),
    "swap": Command(
        name="swap",
        description="Alias for /agent",
        aliases=["agent"],
        requires_arg=True,
    ),
    "toolset": Command(
        name="toolset",
        description="Change toolset (codex/default/gemini)",
        requires_arg=True,
    ),
    "yolo": Command(
        name="yolo",
        description="Toggle YOLO mode on/off",
    ),
    "session": Command(
        name="session",
        description="Show current session info",
    ),
    "save": Command(
        name="save",
        description="Force save current session",
    ),
}

# Add aliases to lookup
for cmd_name, cmd in list(COMMANDS.items()):
    if cmd.aliases:
        for alias in cmd.aliases:
            if alias not in COMMANDS:
                COMMANDS[alias] = cmd


class CommandRegistry:
    """Registry for slash commands."""

    def __init__(self) -> None:
        self.commands = COMMANDS

    def is_valid(self, name: str) -> bool:
        """Check if command name is valid."""
        return name in self.commands

    def get(self, name: str) -> Command | None:
        """Get command by name."""
        return self.commands.get(name)

    def get_help_text(self) -> str:
        """Generate help text for all commands."""
        lines = ["Available commands:", ""]

        # Deduplicate by showing only primary commands
        seen = set()
        for name, cmd in sorted(self.commands.items()):
            if cmd.name in seen:
                continue
            seen.add(cmd.name)

            alias_text = ""
            if cmd.aliases:
                alias_text = f" (aliases: {', '.join('/' + a for a in cmd.aliases)})"

            lines.append(f"  /{name}: {cmd.description}{alias_text}")

        return "\n".join(lines)
