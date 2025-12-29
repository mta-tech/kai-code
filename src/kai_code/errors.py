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
