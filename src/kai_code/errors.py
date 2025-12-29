"""Actionable error framework for enhanced user-friendly error messages.

This module provides structured error types with actionable suggestions,
recovery commands, and related items to help users understand and fix errors.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Literal


class ErrorType(Enum):
    """Categorization of error types for actionable error messages.

    Each error type corresponds to a specific class of errors that can occur
    during CLI operations, enabling targeted suggestions and recovery options.
    """

    # File-related errors
    FILE_NOT_FOUND = "file_not_found"
    FILE_PERMISSION_DENIED = "file_permission_denied"
    INVALID_FILE_TYPE = "invalid_file_type"
    FILE_READ_ERROR = "file_read_error"
    FILE_WRITE_ERROR = "file_write_error"

    # Command-related errors
    COMMAND_NOT_FOUND = "command_not_found"
    INVALID_FLAG = "invalid_flag"
    MISSING_ARGUMENT = "missing_argument"
    COMMAND_EXECUTION_ERROR = "command_execution_error"

    # Configuration errors
    API_KEY_MISSING = "api_key_missing"
    API_KEY_INVALID = "api_key_invalid"
    MODEL_NOT_AVAILABLE = "model_not_available"
    CONFIGURATION_ERROR = "configuration_error"

    # Skill-related errors
    SKILL_NOT_FOUND = "skill_not_found"
    SKILL_LOAD_ERROR = "skill_load_error"
    SKILL_PARSE_ERROR = "skill_parse_error"

    # Agent-related errors
    AGENT_CREATION_ERROR = "agent_creation_error"
    AGENT_NOT_FOUND = "agent_not_found"
    SESSION_ERROR = "session_error"

    # Network/API errors
    NETWORK_ERROR = "network_error"
    API_ERROR = "api_error"
    TIMEOUT_ERROR = "timeout_error"
    RATE_LIMIT_ERROR = "rate_limit_error"

    # Permission errors
    PERMISSION_DENIED = "permission_denied"
    TOOL_NOT_ALLOWED = "tool_not_allowed"

    # DBT-specific errors
    DBT_CONNECTION_ERROR = "dbt_connection_error"
    DBT_MODEL_NOT_FOUND = "dbt_model_not_found"
    DBT_COMMAND_ERROR = "dbt_command_error"

    # Generic errors
    VALIDATION_ERROR = "validation_error"
    INTERNAL_ERROR = "internal_error"
    UNKNOWN_ERROR = "unknown_error"


ErrorSeverity = Literal["error", "warning", "info"]


@dataclass
class ActionableError:
    """A structured error with actionable suggestions and recovery options.

    This class represents errors in a way that provides users with:
    - Clear understanding of what went wrong (message)
    - Categorization of the error type (error_type)
    - Actionable suggestions to fix the issue (suggestions)
    - Commands they can run to recover (recovery_commands)
    - Related items that might help (related_items)

    Example:
        error = ActionableError(
            error_type=ErrorType.FILE_NOT_FOUND,
            message="File 'config.yaml' not found",
            suggestions=[
                "Check if the file path is correct",
                "Ensure the file exists in the current directory",
            ],
            recovery_commands=[
                "ls -la",
                "find . -name '*.yaml'",
            ],
            related_items=["config.yml", "conf.yaml"],
        )
    """

    error_type: ErrorType
    message: str
    suggestions: list[str] = field(default_factory=list)
    recovery_commands: list[str] = field(default_factory=list)
    related_items: list[str] = field(default_factory=list)
    severity: ErrorSeverity = "error"
    context: dict[str, str] = field(default_factory=dict)

    def __str__(self) -> str:
        """Return a simple string representation of the error."""
        return f"[{self.error_type.value}] {self.message}"

    def has_suggestions(self) -> bool:
        """Check if this error has any suggestions."""
        return bool(self.suggestions)

    def has_recovery_commands(self) -> bool:
        """Check if this error has any recovery commands."""
        return bool(self.recovery_commands)

    def has_related_items(self) -> bool:
        """Check if this error has any related items."""
        return bool(self.related_items)

    def to_dict(self) -> dict:
        """Convert the error to a dictionary representation."""
        return {
            "error_type": self.error_type.value,
            "message": self.message,
            "suggestions": self.suggestions,
            "recovery_commands": self.recovery_commands,
            "related_items": self.related_items,
            "severity": self.severity,
            "context": self.context,
        }

    @classmethod
    def from_dict(cls, data: dict) -> ActionableError:
        """Create an ActionableError from a dictionary."""
        error_type_value = data.get("error_type", "unknown_error")
        try:
            error_type = ErrorType(error_type_value)
        except ValueError:
            error_type = ErrorType.UNKNOWN_ERROR

        return cls(
            error_type=error_type,
            message=data.get("message", "An unknown error occurred"),
            suggestions=data.get("suggestions", []),
            recovery_commands=data.get("recovery_commands", []),
            related_items=data.get("related_items", []),
            severity=data.get("severity", "error"),
            context=data.get("context", {}),
        )


class ActionableErrorException(Exception):
    """Exception wrapper for ActionableError.

    This allows ActionableError to be raised as an exception while
    preserving all the structured error information.

    Example:
        raise ActionableErrorException(
            ActionableError(
                error_type=ErrorType.FILE_NOT_FOUND,
                message="Configuration file not found",
                suggestions=["Create a config file"],
            )
        )
    """

    def __init__(self, error: ActionableError) -> None:
        self.error = error
        super().__init__(str(error))

    def __str__(self) -> str:
        return str(self.error)


class ErrorRenderer:
    """Renders ActionableError instances as Rich console output.

    This class formats ActionableError into visually appealing Rich console
    output with colored sections for error header, explanation, suggestions,
    recovery commands, and related items.

    The styling matches existing Rich UI patterns in the kai-code codebase.

    Example:
        renderer = ErrorRenderer()
        renderer.render(error)

        # Or render to a string (for testing or custom output)
        output = renderer.render_to_string(error)
    """

    # Color scheme matching rich_config.py COLORS
    COLORS = {
        "error": "red",
        "warning": "yellow",
        "info": "blue",
        "primary": "#10b981",
        "dim": "#6b7280",
        "suggestion": "cyan",
        "command": "#fbbf24",  # tool color
        "related": "magenta",
    }

    # Icons for different severity levels
    ICONS = {
        "error": "✗",
        "warning": "⚠",
        "info": "ℹ",
    }

    def __init__(self, console: "Console | None" = None) -> None:
        """Initialize the ErrorRenderer.

        Args:
            console: Rich Console instance. If None, creates a new one.
        """
        if console is None:
            from rich.console import Console

            console = Console(highlight=False)
        self._console = console

    @property
    def console(self) -> "Console":
        """Get the Rich console instance."""
        return self._console

    def render(self, error: ActionableError) -> None:
        """Render an ActionableError to the console.

        Args:
            error: The ActionableError to render.
        """
        from rich import box
        from rich.panel import Panel
        from rich.text import Text

        # Build the content
        content = self._build_content(error)

        # Determine border color based on severity
        border_color = self.COLORS.get(error.severity, self.COLORS["error"])

        # Build the header title
        icon = self.ICONS.get(error.severity, self.ICONS["error"])
        error_type_display = error.error_type.value.replace("_", " ").title()
        title = f"{icon} {error_type_display}"

        # Create and print the panel
        panel = Panel(
            content,
            title=f"[bold {border_color}]{title}[/bold {border_color}]",
            border_style=border_color,
            box=box.ROUNDED,
            padding=(0, 1),
        )

        self._console.print()
        self._console.print(panel)
        self._console.print()

    def render_to_string(self, error: ActionableError) -> str:
        """Render an ActionableError to a string.

        Useful for testing or when you need the output as a string.

        Args:
            error: The ActionableError to render.

        Returns:
            The rendered error as a string with ANSI escape codes.
        """
        from io import StringIO

        from rich.console import Console

        string_io = StringIO()
        temp_console = Console(file=string_io, force_terminal=True, highlight=False)
        temp_renderer = ErrorRenderer(console=temp_console)
        temp_renderer.render(error)
        return string_io.getvalue()

    def render_to_text(self, error: ActionableError) -> "Text":
        """Render an ActionableError to a Rich Text object.

        Useful for embedding the error in other Rich renderables.

        Args:
            error: The ActionableError to render.

        Returns:
            A Rich Text object containing the formatted error.
        """
        return self._build_content(error)

    def _build_content(self, error: ActionableError) -> "Text":
        """Build the Rich Text content for an error.

        Args:
            error: The ActionableError to format.

        Returns:
            A Rich Text object with the formatted content.
        """
        from rich.text import Text

        content = Text()

        # Main error message
        severity_color = self.COLORS.get(error.severity, self.COLORS["error"])
        content.append(error.message, style=f"bold {severity_color}")
        content.append("\n")

        # Suggestions section
        if error.has_suggestions():
            content.append("\n")
            content.append("💡 ", style="bold")
            content.append("Suggestions:", style=f"bold {self.COLORS['suggestion']}")
            content.append("\n")
            for suggestion in error.suggestions:
                content.append("   • ", style=self.COLORS["dim"])
                content.append(suggestion, style=self.COLORS["suggestion"])
                content.append("\n")

        # Recovery commands section
        if error.has_recovery_commands():
            content.append("\n")
            content.append("🔧 ", style="bold")
            content.append("Try these commands:", style=f"bold {self.COLORS['command']}")
            content.append("\n")
            for command in error.recovery_commands:
                content.append("   $ ", style=self.COLORS["dim"])
                content.append(command, style=f"bold {self.COLORS['command']}")
                content.append("\n")

        # Related items section
        if error.has_related_items():
            content.append("\n")
            content.append("🔍 ", style="bold")
            content.append("Did you mean:", style=f"bold {self.COLORS['related']}")
            content.append("\n")
            for item in error.related_items:
                content.append("   → ", style=self.COLORS["dim"])
                content.append(item, style=f"bold {self.COLORS['related']}")
                content.append("\n")

        # Context information (if any)
        if error.context:
            content.append("\n")
            content.append("📋 ", style="bold")
            content.append("Context:", style=f"bold {self.COLORS['dim']}")
            content.append("\n")
            for key, value in error.context.items():
                content.append(f"   {key}: ", style=self.COLORS["dim"])
                content.append(value, style="dim italic")
                content.append("\n")

        # Remove trailing newline
        if content.plain.endswith("\n"):
            content = Text(content.plain.rstrip("\n"))
            # Re-apply styles by rebuilding
            content = self._build_content_no_trailing(error)

        return content

    def _build_content_no_trailing(self, error: ActionableError) -> "Text":
        """Build content without trailing newline.

        Args:
            error: The ActionableError to format.

        Returns:
            A Rich Text object with the formatted content (no trailing newline).
        """
        from rich.text import Text

        content = Text()

        # Main error message
        severity_color = self.COLORS.get(error.severity, self.COLORS["error"])
        content.append(error.message, style=f"bold {severity_color}")

        # Suggestions section
        if error.has_suggestions():
            content.append("\n\n")
            content.append("💡 ", style="bold")
            content.append("Suggestions:", style=f"bold {self.COLORS['suggestion']}")
            for i, suggestion in enumerate(error.suggestions):
                content.append("\n")
                content.append("   • ", style=self.COLORS["dim"])
                content.append(suggestion, style=self.COLORS["suggestion"])

        # Recovery commands section
        if error.has_recovery_commands():
            content.append("\n\n")
            content.append("🔧 ", style="bold")
            content.append("Try these commands:", style=f"bold {self.COLORS['command']}")
            for command in error.recovery_commands:
                content.append("\n")
                content.append("   $ ", style=self.COLORS["dim"])
                content.append(command, style=f"bold {self.COLORS['command']}")

        # Related items section
        if error.has_related_items():
            content.append("\n\n")
            content.append("🔍 ", style="bold")
            content.append("Did you mean:", style=f"bold {self.COLORS['related']}")
            for item in error.related_items:
                content.append("\n")
                content.append("   → ", style=self.COLORS["dim"])
                content.append(item, style=f"bold {self.COLORS['related']}")

        # Context information (if any)
        if error.context:
            content.append("\n\n")
            content.append("📋 ", style="bold")
            content.append("Context:", style=f"bold {self.COLORS['dim']}")
            for key, value in error.context.items():
                content.append("\n")
                content.append(f"   {key}: ", style=self.COLORS["dim"])
                content.append(value, style="dim italic")

        return content

    def render_simple(self, error: ActionableError) -> None:
        """Render an ActionableError as simple inline text (without panel).

        Useful for less intrusive error display in some contexts.

        Args:
            error: The ActionableError to render.
        """
        severity_color = self.COLORS.get(error.severity, self.COLORS["error"])
        icon = self.ICONS.get(error.severity, self.ICONS["error"])

        # Main message
        self._console.print(f"[{severity_color}]{icon} {error.message}[/{severity_color}]")

        # Suggestions (inline)
        if error.has_suggestions():
            for suggestion in error.suggestions:
                self._console.print(
                    f"  [dim]•[/dim] [{self.COLORS['suggestion']}]{suggestion}[/{self.COLORS['suggestion']}]"
                )

        # Related items (inline)
        if error.has_related_items():
            items_str = ", ".join(error.related_items[:3])  # Limit to 3
            if len(error.related_items) > 3:
                items_str += ", ..."
            self._console.print(
                f"  [dim]Did you mean:[/dim] [{self.COLORS['related']}]{items_str}[/{self.COLORS['related']}]"
            )


# Convenience function for quick rendering
def render_error(error: ActionableError, console: "Console | None" = None) -> None:
    """Render an ActionableError to the console.

    This is a convenience function that creates an ErrorRenderer and renders
    the error. For multiple errors, create an ErrorRenderer instance directly.

    Args:
        error: The ActionableError to render.
        console: Optional Rich Console instance.
    """
    renderer = ErrorRenderer(console=console)
    renderer.render(error)
