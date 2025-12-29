from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from deepagents.backends.protocol import EditResult, ExecuteResponse, WriteResult

from .backend import KaiLocalBackend
from .patching import apply_patch as apply_patch_impl


@dataclass(frozen=True)
class LettaTool:
    name: str
    description: str
    args_json_schema: dict[str, Any]
    handler: Callable[[dict[str, Any]], str]


def _json(obj: Any) -> str:
    return json.dumps(obj, indent=2, sort_keys=True)


def build_default_tools(*, root_dir: Path) -> list[LettaTool]:
    backend = KaiLocalBackend(root_dir)

    def _ls(args: dict[str, Any]) -> str:
        path = str(args.get("path") or "/")
        return _json(backend.ls_info(path))

    def _read_file(args: dict[str, Any]) -> str:
        file_path = str(args["file_path"])
        offset = int(args.get("offset", 0) or 0)
        limit = int(args.get("limit", 2000) or 2000)
        return backend.read(file_path, offset=offset, limit=limit)

    def _glob(args: dict[str, Any]) -> str:
        pattern = str(args["pattern"])
        path = str(args.get("path") or "/")
        return _json(backend.glob_info(pattern, path=path))

    def _grep(args: dict[str, Any]) -> str:
        pattern = str(args["pattern"])
        path = args.get("path")
        glob = args.get("glob")
        return str(backend.grep_raw(pattern, path=path, glob=glob))

    def _write_file(args: dict[str, Any]) -> str:
        file_path = str(args["file_path"])
        content = str(args.get("content") or "")
        res: WriteResult = backend.write(file_path, content)
        return _json({"ok": res.error is None, "error": res.error})

    def _edit_file(args: dict[str, Any]) -> str:
        file_path = str(args["file_path"])
        old_string = str(args.get("old_string") or "")
        new_string = str(args.get("new_string") or "")
        replace_all = bool(args.get("replace_all", False))
        res: EditResult = backend.edit(file_path, old_string, new_string, replace_all=replace_all)
        return _json({"ok": res.error is None, "error": res.error})

    def _execute(args: dict[str, Any]) -> str:
        command = str(args["command"])
        res: ExecuteResponse = backend.execute(command)
        return _json(
            {
                "exit_code": res.exit_code,
                "truncated": bool(getattr(res, "truncated", False)),
                "output": res.output,
            }
        )

    def _apply_patch(args: dict[str, Any]) -> str:
        patch = str(args["patch"])
        res = apply_patch_impl(root_dir=root_dir, patch=patch)
        return _json(res)

    return [
        LettaTool(
            name="ls",
            description="List files/directories under a path",
            args_json_schema={
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": [],
            },
            handler=_ls,
        ),
        LettaTool(
            name="read_file",
            description="Read a text file",
            args_json_schema={
                "type": "object",
                "properties": {
                    "file_path": {"type": "string"},
                    "offset": {"type": "integer"},
                    "limit": {"type": "integer"},
                },
                "required": ["file_path"],
            },
            handler=_read_file,
        ),
        LettaTool(
            name="glob",
            description="Find file paths matching a glob",
            args_json_schema={
                "type": "object",
                "properties": {
                    "pattern": {"type": "string"},
                    "path": {"type": "string"},
                },
                "required": ["pattern"],
            },
            handler=_glob,
        ),
        LettaTool(
            name="grep",
            description="Search file contents (ripgrep-like)",
            args_json_schema={
                "type": "object",
                "properties": {
                    "pattern": {"type": "string"},
                    "path": {"type": ["string", "null"]},
                    "glob": {"type": ["string", "null"]},
                },
                "required": ["pattern"],
            },
            handler=_grep,
        ),
        LettaTool(
            name="write_file",
            description="Write an entire file",
            args_json_schema={
                "type": "object",
                "properties": {"file_path": {"type": "string"}, "content": {"type": "string"}},
                "required": ["file_path", "content"],
            },
            handler=_write_file,
        ),
        LettaTool(
            name="edit_file",
            description="String replace within a file",
            args_json_schema={
                "type": "object",
                "properties": {
                    "file_path": {"type": "string"},
                    "old_string": {"type": "string"},
                    "new_string": {"type": "string"},
                    "replace_all": {"type": "boolean"},
                },
                "required": ["file_path", "old_string", "new_string"],
            },
            handler=_edit_file,
        ),
        LettaTool(
            name="execute",
            description="Execute a shell command in the repo root",
            args_json_schema={
                "type": "object",
                "properties": {"command": {"type": "string"}},
                "required": ["command"],
            },
            handler=_execute,
        ),
        LettaTool(
            name="apply_patch",
            description="Apply a unified patch to files",
            args_json_schema={
                "type": "object",
                "properties": {"patch": {"type": "string"}},
                "required": ["patch"],
            },
            handler=_apply_patch,
        ),
    ]
