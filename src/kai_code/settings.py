from __future__ import annotations

import json
from dataclasses import asdict, dataclass
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
class CompactionConfig:
    """Configuration for auto-compaction feature."""

    enabled: bool = True
    threshold: float = 0.85  # 85% context usage triggers compaction
    recent_window_turns: int = 10  # Keep last N turns verbatim
    min_time_between: int = 300  # 5 minutes in seconds
    max_summary_tokens: int = 1000  # Target size per summary


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

    # Compaction
    compaction: CompactionConfig | None = None


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


def _get_compaction_config(d: dict[str, Any]) -> CompactionConfig | None:
    """Extract compaction configuration from settings dict."""
    if "compaction" not in d:
        return None

    c = d["compaction"]
    if not isinstance(c, dict):
        return None

    return CompactionConfig(
        enabled=c.get("enabled", True),
        threshold=c.get("threshold", 0.85),
        recent_window_turns=c.get("recent_window_turns", 10),
        min_time_between=c.get("min_time_between", 300),
        max_summary_tokens=c.get("max_summary_tokens", 1000),
    )


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

    # Merge compaction config with field-level precedence: local > project > global > defaults
    # Only create config if explicitly set, then merge at field level
    compaction = None

    for d in [g, p, l]:
        if "compaction" in d and isinstance(d["compaction"], dict):
            c = d["compaction"]
            if compaction is None:
                # First compaction config - start with defaults then override with explicit values
                compaction = CompactionConfig()
            # Merge at field level: only override fields that are explicitly present
            if "enabled" in c:
                compaction.enabled = c["enabled"]
            if "threshold" in c:
                compaction.threshold = c["threshold"]
            if "recent_window_turns" in c:
                compaction.recent_window_turns = c["recent_window_turns"]
            if "min_time_between" in c:
                compaction.min_time_between = c["min_time_between"]
            if "max_summary_tokens" in c:
                compaction.max_summary_tokens = c["max_summary_tokens"]

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
        compaction=compaction,
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


# Fields that should not be exported (session-specific)
_SESSION_FIELDS = {"last_session", "agents"}


def settings_to_dict(settings: KaiSettings, *, exclude_session_fields: bool = True) -> dict[str, Any]:
    """Convert KaiSettings dataclass to a dict for export.

    Filters out None values and optionally session-specific fields to produce
    a clean JSON-serializable dictionary.

    Args:
        settings: The KaiSettings instance to convert.
        exclude_session_fields: If True, exclude session-specific fields
            (last_session, agents). Defaults to True.

    Returns:
        A dictionary with non-None values, optionally excluding session fields.
    """
    data = asdict(settings)

    # Filter out None values and optionally session-specific fields
    result: dict[str, Any] = {}
    for key, value in data.items():
        if value is None:
            continue
        if exclude_session_fields and key in _SESSION_FIELDS:
            continue
        result[key] = value

    return result


def export_settings(root_dir: Path, output_path: Path) -> tuple[bool, str]:
    """Export merged settings to a JSON file.

    Loads the merged settings from global/project/local files and writes
    configuration settings (excluding session-specific fields) to output_path.

    Args:
        root_dir: Project root directory for loading settings.
        output_path: Path to write the exported settings JSON file.

    Returns:
        A tuple of (success, message) indicating the result.
    """
    try:
        settings = load_settings(root_dir)
        export_data = settings_to_dict(settings, exclude_session_fields=True)

        _write_json(output_path, export_data)

        field_count = len(export_data)
        return True, f"Exported {field_count} setting(s) to {output_path}"

    except Exception as e:
        return False, f"Failed to export settings: {e}"


# Valid configuration keys (both snake_case and camelCase versions)
# Excludes session-specific fields which should not be imported
_VALID_CONFIG_KEYS = {
    # snake_case
    "default_model",
    "default_toolset",
    "permission_mode",
    "allowed_tools",
    "disallowed_tools",
    "allowed_commands",
    "disallowed_commands",
    # camelCase
    "defaultModel",
    "defaultToolset",
    "permissionMode",
    "allowedTools",
    "disallowedTools",
    "allowedCommands",
    "disallowedCommands",
}

# Expected types for each setting field
# Keys that expect string values
_STRING_KEYS = {
    "default_model",
    "defaultModel",
    "default_toolset",
    "defaultToolset",
    "permission_mode",
    "permissionMode",
}

# Keys that expect list of strings
_LIST_KEYS = {
    "allowed_tools",
    "allowedTools",
    "disallowed_tools",
    "disallowedTools",
    "allowed_commands",
    "allowedCommands",
    "disallowed_commands",
    "disallowedCommands",
}


def validate_settings_dict(data: dict[str, Any]) -> list[str]:
    """Validate that a settings dict contains only valid KaiSettings fields with correct types.

    Validates that:
    - All keys are valid KaiSettings configuration fields (snake_case or camelCase)
    - Session-specific fields (last_session, agents) are not present
    - Value types match expected types (strings or lists of strings)

    Args:
        data: Dictionary of settings to validate.

    Returns:
        A list of validation error messages. Empty list if all valid.
    """
    errors: list[str] = []

    if not isinstance(data, dict):
        return ["Settings must be a dictionary"]

    for key, value in data.items():
        # Check for session-specific fields
        if key in _SESSION_FIELDS:
            errors.append(f"Cannot import session-specific field: {key}")
            continue

        # Check for unknown keys
        if key not in _VALID_CONFIG_KEYS:
            errors.append(f"Unknown settings key: {key}")
            continue

        # Skip None values (they're valid but will be filtered)
        if value is None:
            continue

        # Validate string fields
        if key in _STRING_KEYS:
            if not isinstance(value, str):
                errors.append(f"Field '{key}' must be a string, got {type(value).__name__}")
            elif not value.strip():
                errors.append(f"Field '{key}' cannot be an empty string")

        # Validate list fields
        elif key in _LIST_KEYS:
            if isinstance(value, str):
                # Strings are acceptable for list fields (will be split by comma)
                pass
            elif isinstance(value, list):
                for i, item in enumerate(value):
                    if not isinstance(item, str):
                        errors.append(f"Field '{key}' item {i} must be a string, got {type(item).__name__}")
            else:
                errors.append(f"Field '{key}' must be a list of strings or comma-separated string, got {type(value).__name__}")

    return errors


def import_settings(input_path: Path, target: str, root_dir: Path) -> tuple[bool, str]:
    """Import settings from a JSON file to a target settings file.

    Reads settings from the input file and merges them with the existing
    settings in the target file (global, project, or local).

    Args:
        input_path: Path to the JSON file containing settings to import.
        target: Target settings file - 'global', 'project', or 'local'.
        root_dir: Project root directory for project/local settings paths.

    Returns:
        A tuple of (success, message) indicating the result.
    """
    # Validate target
    valid_targets = {"global", "project", "local"}
    if target not in valid_targets:
        return False, f"Invalid target '{target}'. Must be one of: {', '.join(sorted(valid_targets))}"

    # Check input file exists
    if not input_path.exists():
        return False, f"Input file not found: {input_path}"

    # Read input file
    try:
        input_data = json.loads(input_path.read_text())
        if not isinstance(input_data, dict):
            return False, "Input file must contain a JSON object"
    except json.JSONDecodeError as e:
        return False, f"Invalid JSON in input file: {e}"
    except Exception as e:
        return False, f"Failed to read input file: {e}"

    # Validate settings using helper function
    validation_errors = validate_settings_dict(input_data)
    if validation_errors:
        return False, f"Invalid settings: {'; '.join(validation_errors)}"

    # No settings to import
    if not input_data:
        return False, "No settings to import (file is empty or contains only null values)"

    # Determine target path
    if target == "global":
        target_path = global_settings_path()
    elif target == "project":
        target_path = project_settings_path(root_dir)
    else:  # local
        target_path = local_settings_path(root_dir)

    try:
        # Read existing settings
        existing_data = _read_json(target_path)

        # Merge imported settings with existing (imported takes precedence)
        merged_data = {**existing_data, **input_data}

        # Write merged settings
        _write_json(target_path, merged_data)

        imported_keys = list(input_data.keys())
        return True, f"Imported {len(imported_keys)} setting(s) to {target} settings: {', '.join(imported_keys)}"

    except Exception as e:
        return False, f"Failed to write settings: {e}"
