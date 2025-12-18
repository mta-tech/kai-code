from __future__ import annotations

from dataclasses import dataclass
from fnmatch import fnmatch
from typing import Any


def _matches_any(value: str, patterns: list[str] | None) -> bool:
    if not patterns:
        return False
    return any(fnmatch(value, p) for p in patterns)


@dataclass(frozen=True)
class PermissionConfig:
    """Simple allow/deny controls.

    This is intentionally minimal (MVP): it is not a full sandbox.
    """

    allowed_tools: list[str] | None = None
    disallowed_tools: list[str] | None = None
    allowed_commands: list[str] | None = None
    disallowed_commands: list[str] | None = None

    def tool_allowed(self, tool_name: str) -> bool:
        if _matches_any(tool_name, self.disallowed_tools):
            return False
        if self.allowed_tools is not None and not _matches_any(tool_name, self.allowed_tools):
            return False
        return True

    def execute_allowed(self, command: str) -> bool:
        if _matches_any(command, self.disallowed_commands):
            return False
        if self.allowed_commands is not None and not _matches_any(command, self.allowed_commands):
            return False
        return True


def permission_denied_message(tool_name: str, args: dict[str, Any] | None = None) -> str:
    if args:
        return f"Permission denied for tool '{tool_name}' with args: {args}"
    return f"Permission denied for tool '{tool_name}'"

