from __future__ import annotations

import json
from pathlib import Path

import pytest

from kai_code.settings import (
    KaiSettings,
    _read_json,
    _write_json,
    export_settings,
    import_settings,
    settings_to_dict,
    validate_settings_dict,
)


# ============================================================
# settings_to_dict tests
# ============================================================


def test_settings_to_dict_basic() -> None:
    """Test settings_to_dict converts KaiSettings to dict."""
    settings = KaiSettings(
        default_model="gpt-4",
        permission_mode="normal",
    )
    result = settings_to_dict(settings)
    assert result == {
        "default_model": "gpt-4",
        "permission_mode": "normal",
    }


def test_settings_to_dict_excludes_none_values() -> None:
    """Test settings_to_dict filters out None values."""
    settings = KaiSettings(
        default_model="gpt-4",
        default_toolset=None,  # Should be excluded
        permission_mode=None,  # Should be excluded
    )
    result = settings_to_dict(settings)
    assert "default_toolset" not in result
    assert "permission_mode" not in result
    assert result == {"default_model": "gpt-4"}


def test_settings_to_dict_excludes_session_fields() -> None:
    """Test settings_to_dict excludes session-specific fields by default."""
    settings = KaiSettings(
        default_model="gpt-4",
        last_session="/path/to/session",
        agents={"agent1": "value1"},
    )
    result = settings_to_dict(settings)
    assert "last_session" not in result
    assert "agents" not in result
    assert result == {"default_model": "gpt-4"}


def test_settings_to_dict_includes_session_fields_when_disabled() -> None:
    """Test settings_to_dict includes session fields when exclude_session_fields=False."""
    settings = KaiSettings(
        default_model="gpt-4",
        last_session="/path/to/session",
        agents={"agent1": "value1"},
    )
    result = settings_to_dict(settings, exclude_session_fields=False)
    assert result == {
        "default_model": "gpt-4",
        "last_session": "/path/to/session",
        "agents": {"agent1": "value1"},
    }


def test_settings_to_dict_with_lists() -> None:
    """Test settings_to_dict handles list fields correctly."""
    settings = KaiSettings(
        allowed_tools=["tool1", "tool2"],
        disallowed_commands=["cmd1"],
    )
    result = settings_to_dict(settings)
    assert result == {
        "allowed_tools": ["tool1", "tool2"],
        "disallowed_commands": ["cmd1"],
    }


def test_settings_to_dict_empty_agents_excluded() -> None:
    """Test that empty agents dict is excluded as a session field."""
    settings = KaiSettings(
        default_model="gpt-4",
        agents={},
    )
    result = settings_to_dict(settings)
    # agents is session field and should be excluded even if empty
    assert "agents" not in result


# ============================================================
# validate_settings_dict tests
# ============================================================


def test_validate_settings_dict_valid_data() -> None:
    """Test validate_settings_dict returns empty list for valid data."""
    data = {
        "default_model": "gpt-4",
        "permission_mode": "normal",
        "allowed_tools": ["tool1", "tool2"],
    }
    errors = validate_settings_dict(data)
    assert errors == []


def test_validate_settings_dict_valid_camelcase() -> None:
    """Test validate_settings_dict accepts camelCase keys."""
    data = {
        "defaultModel": "gpt-4",
        "permissionMode": "normal",
        "allowedTools": ["tool1"],
    }
    errors = validate_settings_dict(data)
    assert errors == []


def test_validate_settings_dict_mixed_case() -> None:
    """Test validate_settings_dict accepts mixed snake_case and camelCase."""
    data = {
        "default_model": "gpt-4",
        "permissionMode": "normal",
    }
    errors = validate_settings_dict(data)
    assert errors == []


def test_validate_settings_dict_rejects_unknown_keys() -> None:
    """Test validate_settings_dict rejects unknown keys."""
    data = {
        "default_model": "gpt-4",
        "unknown_key": "value",
    }
    errors = validate_settings_dict(data)
    assert len(errors) == 1
    assert "Unknown settings key: unknown_key" in errors[0]


def test_validate_settings_dict_rejects_session_fields() -> None:
    """Test validate_settings_dict rejects session-specific fields."""
    data = {
        "default_model": "gpt-4",
        "last_session": "/path/to/session",
        "agents": {"agent1": "value"},
    }
    errors = validate_settings_dict(data)
    assert len(errors) == 2
    assert any("last_session" in e for e in errors)
    assert any("agents" in e for e in errors)


def test_validate_settings_dict_rejects_wrong_type_string() -> None:
    """Test validate_settings_dict rejects non-string for string fields."""
    data = {
        "default_model": 123,  # Should be string
    }
    errors = validate_settings_dict(data)
    assert len(errors) == 1
    assert "must be a string" in errors[0]


def test_validate_settings_dict_rejects_empty_string() -> None:
    """Test validate_settings_dict rejects empty strings for string fields."""
    data = {
        "default_model": "  ",  # Empty after strip
    }
    errors = validate_settings_dict(data)
    assert len(errors) == 1
    assert "cannot be an empty string" in errors[0]


def test_validate_settings_dict_rejects_wrong_type_list() -> None:
    """Test validate_settings_dict rejects non-list/string for list fields."""
    data = {
        "allowed_tools": 123,  # Should be list or string
    }
    errors = validate_settings_dict(data)
    assert len(errors) == 1
    assert "must be a list of strings" in errors[0]


def test_validate_settings_dict_accepts_comma_string_for_list() -> None:
    """Test validate_settings_dict accepts comma-separated string for list fields."""
    data = {
        "allowed_tools": "tool1, tool2, tool3",
    }
    errors = validate_settings_dict(data)
    assert errors == []


def test_validate_settings_dict_rejects_non_string_in_list() -> None:
    """Test validate_settings_dict rejects non-string items in list fields."""
    data = {
        "allowed_tools": ["tool1", 123, "tool3"],
    }
    errors = validate_settings_dict(data)
    assert len(errors) == 1
    assert "item 1 must be a string" in errors[0]


def test_validate_settings_dict_allows_none_values() -> None:
    """Test validate_settings_dict allows None values (they'll be filtered)."""
    data = {
        "default_model": None,
        "permission_mode": None,
    }
    errors = validate_settings_dict(data)
    assert errors == []


def test_validate_settings_dict_non_dict_input() -> None:
    """Test validate_settings_dict handles non-dict input."""
    errors = validate_settings_dict("not a dict")  # type: ignore
    assert errors == ["Settings must be a dictionary"]


# ============================================================
# export_settings tests
# ============================================================


def test_export_settings_creates_valid_json_file(tmp_path: Path) -> None:
    """Test export_settings creates a valid JSON file."""
    # Setup: create project settings
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    kai_dir = project_dir / ".kai"
    kai_dir.mkdir()
    settings_file = kai_dir / "settings.json"
    _write_json(settings_file, {"default_model": "gpt-4", "permission_mode": "normal"})

    # Export
    output_path = tmp_path / "exported.json"
    success, message = export_settings(project_dir, output_path)

    # Verify
    assert success is True
    assert "Exported" in message
    assert output_path.exists()

    # Verify JSON is valid
    exported_data = json.loads(output_path.read_text())
    assert isinstance(exported_data, dict)
    assert exported_data.get("default_model") == "gpt-4"


def test_export_settings_excludes_session_fields(tmp_path: Path) -> None:
    """Test export_settings excludes session-specific fields."""
    # Setup: create local settings with session fields
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    kai_dir = project_dir / ".kai"
    kai_dir.mkdir()
    local_settings_file = kai_dir / "settings.local.json"
    _write_json(
        local_settings_file,
        {
            "default_model": "gpt-4",
            "last_session": "/path/to/session",
            "agents": {"agent1": "value"},
        },
    )

    # Export
    output_path = tmp_path / "exported.json"
    success, message = export_settings(project_dir, output_path)

    # Verify
    assert success is True
    exported_data = json.loads(output_path.read_text())
    assert "default_model" in exported_data
    assert "last_session" not in exported_data
    assert "agents" not in exported_data


def test_export_settings_with_empty_settings(tmp_path: Path) -> None:
    """Test export_settings works with empty settings."""
    # Setup: project with no settings
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    # Export
    output_path = tmp_path / "exported.json"
    success, message = export_settings(project_dir, output_path)

    # Verify
    assert success is True
    assert output_path.exists()
    exported_data = json.loads(output_path.read_text())
    assert exported_data == {}


def test_export_settings_reports_field_count(tmp_path: Path) -> None:
    """Test export_settings reports correct field count in message."""
    # Setup
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    kai_dir = project_dir / ".kai"
    kai_dir.mkdir()
    settings_file = kai_dir / "settings.json"
    _write_json(
        settings_file,
        {
            "default_model": "gpt-4",
            "permission_mode": "normal",
            "allowed_tools": ["tool1"],
        },
    )

    # Export
    output_path = tmp_path / "exported.json"
    success, message = export_settings(project_dir, output_path)

    # Verify
    assert success is True
    assert "3 setting(s)" in message


def test_export_settings_creates_parent_directories(tmp_path: Path) -> None:
    """Test export_settings creates parent directories for output path."""
    # Setup
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    # Export to nested path that doesn't exist
    output_path = tmp_path / "nested" / "dir" / "exported.json"
    success, message = export_settings(project_dir, output_path)

    # Verify
    assert success is True
    assert output_path.exists()


# ============================================================
# import_settings tests
# ============================================================


def test_import_settings_reads_and_applies_settings(tmp_path: Path) -> None:
    """Test import_settings reads JSON and applies to target settings file."""
    # Setup: create input file
    input_file = tmp_path / "input.json"
    _write_json(input_file, {"default_model": "gpt-4", "permission_mode": "normal"})

    project_dir = tmp_path / "project"
    project_dir.mkdir()

    # Import to project settings
    success, message = import_settings(input_file, "project", project_dir)

    # Verify
    assert success is True
    assert "Imported 2 setting(s)" in message

    # Check project settings were created
    settings_file = project_dir / ".kai" / "settings.json"
    assert settings_file.exists()
    written_data = json.loads(settings_file.read_text())
    assert written_data["default_model"] == "gpt-4"
    assert written_data["permission_mode"] == "normal"


def test_import_settings_to_global(tmp_path: Path, monkeypatch) -> None:
    """Test import_settings works with target='global'."""
    # Setup: create input file
    input_file = tmp_path / "input.json"
    _write_json(input_file, {"default_model": "gpt-4"})

    # Mock home directory
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    monkeypatch.setenv("HOME", str(fake_home))

    # Import to global
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    success, message = import_settings(input_file, "global", project_dir)

    # Verify
    assert success is True
    assert "global settings" in message

    # Check global settings were created
    global_settings = fake_home / ".kai" / "settings.json"
    assert global_settings.exists()


def test_import_settings_to_local(tmp_path: Path) -> None:
    """Test import_settings works with target='local'."""
    # Setup: create input file
    input_file = tmp_path / "input.json"
    _write_json(input_file, {"default_model": "gpt-4"})

    project_dir = tmp_path / "project"
    project_dir.mkdir()

    # Import to local
    success, message = import_settings(input_file, "local", project_dir)

    # Verify
    assert success is True
    assert "local settings" in message

    # Check local settings were created
    local_settings = project_dir / ".kai" / "settings.local.json"
    assert local_settings.exists()


def test_import_settings_merges_with_existing(tmp_path: Path) -> None:
    """Test import_settings merges with existing settings."""
    # Setup: create existing settings
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    kai_dir = project_dir / ".kai"
    kai_dir.mkdir()
    settings_file = kai_dir / "settings.json"
    _write_json(settings_file, {"default_model": "old-model", "permission_mode": "strict"})

    # Create input file with partial update
    input_file = tmp_path / "input.json"
    _write_json(input_file, {"default_model": "new-model"})

    # Import
    success, message = import_settings(input_file, "project", project_dir)

    # Verify
    assert success is True
    written_data = json.loads(settings_file.read_text())
    # New value should be applied
    assert written_data["default_model"] == "new-model"
    # Existing value should be preserved
    assert written_data["permission_mode"] == "strict"


def test_import_settings_invalid_target(tmp_path: Path) -> None:
    """Test import_settings rejects invalid target."""
    input_file = tmp_path / "input.json"
    _write_json(input_file, {"default_model": "gpt-4"})

    project_dir = tmp_path / "project"
    project_dir.mkdir()

    success, message = import_settings(input_file, "invalid", project_dir)

    assert success is False
    assert "Invalid target" in message


def test_import_settings_file_not_found(tmp_path: Path) -> None:
    """Test import_settings handles missing input file."""
    nonexistent_file = tmp_path / "nonexistent.json"
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    success, message = import_settings(nonexistent_file, "project", project_dir)

    assert success is False
    assert "not found" in message


def test_import_settings_invalid_json(tmp_path: Path) -> None:
    """Test import_settings handles invalid JSON."""
    # Create file with invalid JSON
    input_file = tmp_path / "invalid.json"
    input_file.write_text("{ not valid json }")

    project_dir = tmp_path / "project"
    project_dir.mkdir()

    success, message = import_settings(input_file, "project", project_dir)

    assert success is False
    assert "Invalid JSON" in message


def test_import_settings_non_dict_json(tmp_path: Path) -> None:
    """Test import_settings rejects non-dict JSON."""
    # Create file with JSON array
    input_file = tmp_path / "array.json"
    input_file.write_text('["item1", "item2"]')

    project_dir = tmp_path / "project"
    project_dir.mkdir()

    success, message = import_settings(input_file, "project", project_dir)

    assert success is False
    assert "must contain a JSON object" in message


def test_import_settings_rejects_invalid_keys(tmp_path: Path) -> None:
    """Test import_settings rejects unknown settings keys."""
    input_file = tmp_path / "input.json"
    _write_json(input_file, {"default_model": "gpt-4", "unknown_key": "value"})

    project_dir = tmp_path / "project"
    project_dir.mkdir()

    success, message = import_settings(input_file, "project", project_dir)

    assert success is False
    assert "Unknown settings key" in message


def test_import_settings_rejects_session_fields(tmp_path: Path) -> None:
    """Test import_settings rejects session-specific fields."""
    input_file = tmp_path / "input.json"
    _write_json(input_file, {"default_model": "gpt-4", "last_session": "/path"})

    project_dir = tmp_path / "project"
    project_dir.mkdir()

    success, message = import_settings(input_file, "project", project_dir)

    assert success is False
    assert "session-specific" in message


def test_import_settings_empty_file(tmp_path: Path) -> None:
    """Test import_settings rejects empty settings file."""
    input_file = tmp_path / "empty.json"
    _write_json(input_file, {})

    project_dir = tmp_path / "project"
    project_dir.mkdir()

    success, message = import_settings(input_file, "project", project_dir)

    assert success is False
    assert "No settings to import" in message


def test_import_settings_camelcase_keys(tmp_path: Path) -> None:
    """Test import_settings accepts camelCase keys."""
    input_file = tmp_path / "input.json"
    _write_json(input_file, {"defaultModel": "gpt-4", "permissionMode": "normal"})

    project_dir = tmp_path / "project"
    project_dir.mkdir()

    success, message = import_settings(input_file, "project", project_dir)

    assert success is True
    settings_file = project_dir / ".kai" / "settings.json"
    written_data = json.loads(settings_file.read_text())
    assert written_data["defaultModel"] == "gpt-4"


# ============================================================
# Round-trip tests (export then import)
# ============================================================


def test_export_import_roundtrip(tmp_path: Path) -> None:
    """Test that exported settings can be imported back correctly."""
    # Setup: create project with settings
    project_dir = tmp_path / "project1"
    project_dir.mkdir()
    kai_dir = project_dir / ".kai"
    kai_dir.mkdir()
    settings_file = kai_dir / "settings.json"
    original_settings = {
        "default_model": "gpt-4",
        "permission_mode": "normal",
        "allowed_tools": ["tool1", "tool2"],
        "disallowed_commands": ["cmd1"],
    }
    _write_json(settings_file, original_settings)

    # Export
    export_file = tmp_path / "exported.json"
    success1, _ = export_settings(project_dir, export_file)
    assert success1 is True

    # Import to a new project
    project_dir2 = tmp_path / "project2"
    project_dir2.mkdir()
    success2, _ = import_settings(export_file, "project", project_dir2)
    assert success2 is True

    # Verify settings match
    imported_file = project_dir2 / ".kai" / "settings.json"
    imported_data = json.loads(imported_file.read_text())
    assert imported_data["default_model"] == "gpt-4"
    assert imported_data["permission_mode"] == "normal"
    assert imported_data["allowed_tools"] == ["tool1", "tool2"]
    assert imported_data["disallowed_commands"] == ["cmd1"]


def test_export_import_preserves_all_config_fields(tmp_path: Path) -> None:
    """Test that all configuration fields survive export/import."""
    # Setup: settings with all config fields
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    kai_dir = project_dir / ".kai"
    kai_dir.mkdir()
    settings_file = kai_dir / "settings.json"
    original_settings = {
        "default_model": "gpt-4",
        "default_toolset": "default",
        "permission_mode": "normal",
        "allowed_tools": ["tool1"],
        "disallowed_tools": ["tool2"],
        "allowed_commands": ["cmd1"],
        "disallowed_commands": ["cmd2"],
    }
    _write_json(settings_file, original_settings)

    # Export and import
    export_file = tmp_path / "exported.json"
    export_settings(project_dir, export_file)

    project_dir2 = tmp_path / "project2"
    project_dir2.mkdir()
    import_settings(export_file, "project", project_dir2)

    # Verify all fields preserved
    imported_file = project_dir2 / ".kai" / "settings.json"
    imported_data = json.loads(imported_file.read_text())
    for key, value in original_settings.items():
        assert imported_data[key] == value, f"Field {key} not preserved"
