from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text())
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")


def global_settings_path() -> Path:
    return Path.home() / ".kai" / "settings.json"


def project_settings_path(root_dir: Path) -> Path:
    return root_dir / ".kai" / "settings.json"


def local_settings_path(root_dir: Path) -> Path:
    return root_dir / ".kai" / "settings.local.json"


@dataclass
class KaiSettings:
    """Merged settings across global/project/local files.

    Precedence: local > project > global. CLI flags override separately.
    """

    default_model: str | None = None
    default_toolset: str | None = None
    permission_mode: str | None = None
    allowed_tools: list[str] | None = None
    disallowed_tools: list[str] | None = None
    allowed_commands: list[str] | None = None
    disallowed_commands: list[str] | None = None

    # Project/local resume
    last_session: str | None = None
    agents: dict[str, str] | None = None


def _merge_lists(base: list[str] | None, override: list[str] | None) -> list[str] | None:
    if override is None:
        return base
    return list(override)


def _merge_dicts(base: dict[str, str] | None, override: dict[str, str] | None) -> dict[str, str] | None:
    if base is None and override is None:
        return None
    out: dict[str, str] = {}
    out.update(base or {})
    out.update(override or {})
    return out


def load_settings(root_dir: Path) -> KaiSettings:
    root_dir = root_dir.resolve()

    g = _read_json(global_settings_path())
    p = _read_json(project_settings_path(root_dir))
    l = _read_json(local_settings_path(root_dir))

    def _get_str(d: dict[str, Any], *keys: str) -> str | None:
        v = None
        for key in keys:
            if key in d:
                v = d.get(key)
                break
        return v if isinstance(v, str) and v.strip() else None

    def _get_list(d: dict[str, Any], *keys: str) -> list[str] | None:
        v = None
        for key in keys:
            if key in d:
                v = d.get(key)
                break
        if v is None:
            return None
        if isinstance(v, list) and all(isinstance(x, str) for x in v):
            return [x for x in v if x]
        if isinstance(v, str):
            parts = [p.strip() for p in v.split(",")]
            parts = [p for p in parts if p]
            return parts
        return None

    def _get_agents(d: dict[str, Any]) -> dict[str, str] | None:
        v = d.get("agents")
        if not isinstance(v, dict):
            return None
        out: dict[str, str] = {}
        for k, val in v.items():
            if isinstance(k, str) and isinstance(val, str) and k:
                out[k] = val
        return out

    # Merge with precedence local > project > global
    default_model = _get_str(g, "default_model", "defaultModel")
    if _get_str(p, "default_model", "defaultModel") is not None:
        default_model = _get_str(p, "default_model", "defaultModel")
    if _get_str(l, "default_model", "defaultModel") is not None:
        default_model = _get_str(l, "default_model", "defaultModel")

    default_toolset = _get_str(g, "default_toolset", "defaultToolset")
    if _get_str(p, "default_toolset", "defaultToolset") is not None:
        default_toolset = _get_str(p, "default_toolset", "defaultToolset")
    if _get_str(l, "default_toolset", "defaultToolset") is not None:
        default_toolset = _get_str(l, "default_toolset", "defaultToolset")

    permission_mode = _get_str(g, "permission_mode", "permissionMode")
    if _get_str(p, "permission_mode", "permissionMode") is not None:
        permission_mode = _get_str(p, "permission_mode", "permissionMode")
    if _get_str(l, "permission_mode", "permissionMode") is not None:
        permission_mode = _get_str(l, "permission_mode", "permissionMode")

    allowed_tools = _merge_lists(_get_list(g, "allowed_tools", "allowedTools"), _get_list(p, "allowed_tools", "allowedTools"))
    allowed_tools = _merge_lists(allowed_tools, _get_list(l, "allowed_tools", "allowedTools"))

    disallowed_tools = _merge_lists(_get_list(g, "disallowed_tools", "disallowedTools"), _get_list(p, "disallowed_tools", "disallowedTools"))
    disallowed_tools = _merge_lists(disallowed_tools, _get_list(l, "disallowed_tools", "disallowedTools"))

    allowed_commands = _merge_lists(_get_list(g, "allowed_commands", "allowedCommands"), _get_list(p, "allowed_commands", "allowedCommands"))
    allowed_commands = _merge_lists(allowed_commands, _get_list(l, "allowed_commands", "allowedCommands"))

    disallowed_commands = _merge_lists(_get_list(g, "disallowed_commands", "disallowedCommands"), _get_list(p, "disallowed_commands", "disallowedCommands"))
    disallowed_commands = _merge_lists(disallowed_commands, _get_list(l, "disallowed_commands", "disallowedCommands"))

    # Resume state belongs to local settings file only.
    last_session = _get_str(l, "last_session")
    agents = _get_agents(l) or {}

    return KaiSettings(
        default_model=default_model,
        default_toolset=default_toolset,
        permission_mode=permission_mode,
        allowed_tools=allowed_tools,
        disallowed_tools=disallowed_tools,
        allowed_commands=allowed_commands,
        disallowed_commands=disallowed_commands,
        last_session=last_session,
        agents=agents,
    )


def migrate_global_settings(root_dir: Path) -> None:
    """Migrate old global-only last_session format to new shape.

    Older versions stored {"last_session": "/abs/path"} in ~/.kai/settings.json.
    Keep that key as-is, but ensure the file remains a dict and writable.
    """
    _ = root_dir
    path = global_settings_path()
    data = _read_json(path)
    if not data:
        return
    # If legacy file is present and parseable, keep it. Just rewrite normalized.
    _write_json(path, data)


def migrate_project_settings(root_dir: Path) -> None:
    """Ensure project settings file exists only when needed.

    Previously we only had settings.local.json. This migration is a no-op unless
    a user already created a project settings file in another shape.
    """
    # Normalize if it exists.
    path = project_settings_path(root_dir)
    data = _read_json(path)
    if not data:
        return
    _write_json(path, data)


def update_local_resume(root_dir: Path, *, last_session: str | None, agents: dict[str, str] | None) -> None:
    """Update local resume fields without clobbering other keys."""
    path = local_settings_path(root_dir)
    data = _read_json(path)
    if last_session is not None:
        data["last_session"] = last_session
    if agents is not None:
        data["agents"] = agents
    _write_json(path, data)


def update_global_last_session(session_path: Path) -> None:
    path = global_settings_path()
    data = _read_json(path)
    data["last_session"] = str(session_path)
    _write_json(path, data)


def load_global_last_session() -> str | None:
    data = _read_json(global_settings_path())
    v = data.get("last_session")
    return v if isinstance(v, str) and v.strip() else None
