from __future__ import annotations

import os
import subprocess
import uuid
from dataclasses import dataclass
from pathlib import Path

from deepagents.backends.filesystem import FilesystemBackend
from deepagents.backends.protocol import EditResult, ExecuteResponse, SandboxBackendProtocol, WriteResult

from .permissions import PermissionConfig, permission_denied_message


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
    ) -> None:
        self._id = f"kai-local-{uuid.uuid4().hex[:10]}"
        self._limits = limits or ExecuteLimits()
        self._env = env
        self._permissions = permissions
        super().__init__(root_dir=root_dir, virtual_mode=virtual_mode)

    @property
    def id(self) -> str:  # type: ignore[override]
        return self._id

    def execute(self, command: str) -> ExecuteResponse:  # type: ignore[override]
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
            output = (e.stdout or "") + (e.stderr or "")
            if not output:
                output = f"Error: command timed out after {self._limits.timeout_seconds}s"
            truncated = False
            if len(output) > self._limits.max_output_chars:
                output = output[: self._limits.max_output_chars]
                truncated = True
            return ExecuteResponse(output=output, exit_code=None, truncated=truncated)

    def ls_info(self, path: str):  # type: ignore[override]
        if self._permissions is not None and not self._permissions.tool_allowed("ls"):
            return []
        return super().ls_info(path)

    def read(self, file_path: str, offset: int = 0, limit: int = 2000) -> str:  # type: ignore[override]
        if self._permissions is not None and not self._permissions.tool_allowed("read_file"):
            return permission_denied_message("read_file", {"file_path": file_path})
        return super().read(file_path, offset=offset, limit=limit)

    def glob_info(self, pattern: str, path: str = "/"):  # type: ignore[override]
        if self._permissions is not None and not self._permissions.tool_allowed("glob"):
            return []
        return super().glob_info(pattern, path=path)

    def grep_raw(self, pattern: str, path: str | None = None, glob: str | None = None):  # type: ignore[override]
        if self._permissions is not None and not self._permissions.tool_allowed("grep"):
            return permission_denied_message("grep", {"path": path, "glob": glob})
        return super().grep_raw(pattern, path=path, glob=glob)

    def write(self, file_path: str, content: str) -> WriteResult:  # type: ignore[override]
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
        if self._permissions is not None and not self._permissions.tool_allowed("edit_file"):
            return EditResult(error=permission_denied_message("edit_file", {"file_path": file_path}))
        return super().edit(file_path, old_string, new_string, replace_all=replace_all)
