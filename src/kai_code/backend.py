from __future__ import annotations

import os
import subprocess
import uuid
from dataclasses import dataclass
from fnmatch import fnmatch
from pathlib import Path

from deepagents.backends.filesystem import FilesystemBackend
from deepagents.backends.protocol import EditResult, ExecuteResponse, SandboxBackendProtocol, WriteResult

from .permissions import PermissionConfig, permission_denied_message
from .progress import ProgressPhase, ToolProgress, get_progress_manager
from .rich_config import rich_settings


@dataclass(frozen=True)
class ExecuteLimits:
    timeout_seconds: int = 60
    max_output_chars: int = 80_000


class KaiLocalBackend(FilesystemBackend, SandboxBackendProtocol):
    """Local-disk backend + local command execution.

    - File operations are scoped to `root_dir` via FilesystemBackend(virtual_mode=True).
    - Command execution uses subprocess with cwd=root_dir.

    This is intended for local developer workflows; it is not a hardened sandbox.
    """

    def __init__(
        self,
        root_dir: str | Path,
        *,
        virtual_mode: bool = True,
        limits: ExecuteLimits | None = None,
        env: dict[str, str] | None = None,
        permissions: PermissionConfig | None = None,
        enabled_tools: list[str] | None = None,
    ) -> None:
        self._id = f"kai-local-{uuid.uuid4().hex[:10]}"
        self._limits = limits or ExecuteLimits()
        self._env = env
        self._permissions = permissions
        self._enabled_tools = enabled_tools
        super().__init__(root_dir=root_dir, virtual_mode=virtual_mode)

    def _tool_enabled(self, tool_name: str) -> bool:
        if self._enabled_tools is None:
            return True
        return any(fnmatch(tool_name, p) for p in self._enabled_tools)

    @property
    def id(self) -> str:  # type: ignore[override]
        return self._id

    def execute(self, command: str) -> ExecuteResponse:  # type: ignore[override]
        if not self._tool_enabled("execute"):
            return ExecuteResponse(output=permission_denied_message("execute", {"command": command}), exit_code=1)
        if self._permissions is not None:
            if not self._permissions.tool_allowed("execute") or not self._permissions.execute_allowed(command):
                return ExecuteResponse(output=permission_denied_message("execute", {"command": command}), exit_code=1)
        try:
            completed = subprocess.run(  # noqa: S603
                command,
                cwd=str(self.cwd),
                shell=True,
                text=True,
                capture_output=True,
                timeout=self._limits.timeout_seconds,
                env={**os.environ, **(self._env or {})},
            )
            output = (completed.stdout or "") + (completed.stderr or "")
            truncated = False
            if len(output) > self._limits.max_output_chars:
                output = output[: self._limits.max_output_chars]
                truncated = True
            return ExecuteResponse(
                output=output,
                exit_code=completed.returncode,
                truncated=truncated,
            )
        except subprocess.TimeoutExpired as e:
            # stdout/stderr can be bytes even when text=True was specified
            stdout = e.stdout or ""
            stderr = e.stderr or ""
            if isinstance(stdout, bytes):
                stdout = stdout.decode("utf-8", errors="replace")
            if isinstance(stderr, bytes):
                stderr = stderr.decode("utf-8", errors="replace")
            output = stdout + stderr
            if not output:
                output = f"Error: command timed out after {self._limits.timeout_seconds}s"
            truncated = False
            if len(output) > self._limits.max_output_chars:
                output = output[: self._limits.max_output_chars]
                truncated = True
            return ExecuteResponse(output=output, exit_code=None, truncated=truncated)

    def ls_info(self, path: str):  # type: ignore[override]
        if not self._tool_enabled("ls"):
            return []
        if self._permissions is not None and not self._permissions.tool_allowed("ls"):
            return []
        return super().ls_info(path)

    def read(self, file_path: str, offset: int = 0, limit: int = 2000) -> str:  # type: ignore[override]
        if not self._tool_enabled("read_file"):
            return permission_denied_message("read_file", {"file_path": file_path})
        if self._permissions is not None and not self._permissions.tool_allowed("read_file"):
            return permission_denied_message("read_file", {"file_path": file_path})

        # Check if progress reporting is enabled and get threshold from settings
        progress_enabled = rich_settings.progress_enabled
        file_size_threshold = rich_settings.progress_file_size_threshold

        progress_manager = get_progress_manager()
        display_name = Path(file_path).name or file_path

        # Check file size for progress reporting
        file_size = 0
        if progress_enabled:
            try:
                # Resolve path relative to cwd (the root_dir from FilesystemBackend)
                resolved = file_path.lstrip("/")
                physical_path = self.cwd / resolved
                file_size = physical_path.stat().st_size if physical_path.exists() else 0
            except (OSError, ValueError):
                file_size = 0

        is_large_file = progress_enabled and file_size >= file_size_threshold

        if is_large_file:
            # Report starting phase for large files
            progress_manager.report(
                ToolProgress(
                    tool_name="read_file",
                    status_message=f"Reading {display_name}...",
                    phase=ProgressPhase.STARTING,
                    percent_complete=0.0,
                )
            )

        # Perform the actual read
        result = super().read(file_path, offset=offset, limit=limit)

        # Count lines for completion message
        line_count = len(result.splitlines()) if result else 0

        if is_large_file:
            # Report completion for large files
            progress_manager.report(
                ToolProgress(
                    tool_name="read_file",
                    status_message=f"Read {line_count} lines",
                    phase=ProgressPhase.COMPLETE,
                    percent_complete=100.0,
                )
            )

        return result

    def glob_info(self, pattern: str, path: str = "/"):  # type: ignore[override]
        if not self._tool_enabled("glob"):
            return []
        if self._permissions is not None and not self._permissions.tool_allowed("glob"):
            return []

        # Check if progress reporting is enabled
        progress_enabled = rich_settings.progress_enabled

        if progress_enabled:
            progress_manager = get_progress_manager()

            # Report starting phase - searching for pattern
            progress_manager.report(
                ToolProgress(
                    tool_name="glob",
                    status_message=f"Searching files matching {pattern}...",
                    phase=ProgressPhase.STARTING,
                )
            )

        # Perform the actual glob operation
        result = super().glob_info(pattern, path=path)

        if progress_enabled:
            # Count results for completion message
            match_count = len(result) if result else 0

            # Report completion phase with match count
            progress_manager.report(
                ToolProgress(
                    tool_name="glob",
                    status_message=f"Found {match_count} matching files",
                    phase=ProgressPhase.COMPLETE,
                )
            )

        return result

    def grep_raw(self, pattern: str, path: str | None = None, glob: str | None = None):  # type: ignore[override]
        if not self._tool_enabled("grep"):
            return permission_denied_message("grep", {"path": path, "glob": glob})
        if self._permissions is not None and not self._permissions.tool_allowed("grep"):
            return permission_denied_message("grep", {"path": path, "glob": glob})

        # Check if progress reporting is enabled
        progress_enabled = rich_settings.progress_enabled

        if progress_enabled:
            progress_manager = get_progress_manager()

            # Build a descriptive message based on search context
            display_pattern = pattern if len(pattern) <= 30 else pattern[:27] + "..."

            # Report starting phase - searching for pattern
            progress_manager.report(
                ToolProgress(
                    tool_name="grep",
                    status_message=f'Searching for "{display_pattern}"...',
                    phase=ProgressPhase.STARTING,
                )
            )

        # Perform the actual grep operation
        result = super().grep_raw(pattern, path=path, glob=glob)

        if progress_enabled:
            # Count matches for completion message (result is typically a string with matches)
            if isinstance(result, str):
                # Count non-empty lines as matches
                match_lines = [line for line in result.splitlines() if line.strip()]
                match_count = len(match_lines)
            else:
                match_count = 0

            # Report completion phase with match count
            progress_manager.report(
                ToolProgress(
                    tool_name="grep",
                    status_message=f"Found {match_count} matches",
                    phase=ProgressPhase.COMPLETE,
                )
            )

        return result

    def write(self, file_path: str, content: str) -> WriteResult:  # type: ignore[override]
        if not self._tool_enabled("write_file"):
            return WriteResult(error=permission_denied_message("write_file", {"file_path": file_path}))
        if self._permissions is not None and not self._permissions.tool_allowed("write_file"):
            return WriteResult(error=permission_denied_message("write_file", {"file_path": file_path}))
        return super().write(file_path, content)

    def edit(
        self,
        file_path: str,
        old_string: str,
        new_string: str,
        replace_all: bool = False,
    ) -> EditResult:  # type: ignore[override]
        if not self._tool_enabled("edit_file"):
            return EditResult(error=permission_denied_message("edit_file", {"file_path": file_path}))
        if self._permissions is not None and not self._permissions.tool_allowed("edit_file"):
            return EditResult(error=permission_denied_message("edit_file", {"file_path": file_path}))
        return super().edit(file_path, old_string, new_string, replace_all=replace_all)
