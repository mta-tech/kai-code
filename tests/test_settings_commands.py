"""Tests for the settings export/import slash command handlers.

Tests the /export-settings and /import-settings command handlers in rich_commands.py.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from kai_code.rich_commands import (
    handle_command,
    _handle_export_settings,
    _handle_import_settings,
)
from kai_code.settings import _write_json


# ============================================================
# /export-settings command tests
# ============================================================


def test_export_settings_command_recognized() -> None:
    """Test /export-settings command is recognized."""
    agent = MagicMock()
    with patch("kai_code.rich_commands.rich_settings") as mock_settings:
        mock_settings.project_root = None  # Will use cwd
        result = handle_command("/export-settings", agent)
    # Command should be handled (returns None, not the input)
    assert result is None


def test_export_settings_default_filename(tmp_path: Path) -> None:
    """Test /export-settings uses default filename 'kai-settings.json'."""
    # Setup project directory
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    kai_dir = project_dir / ".kai"
    kai_dir.mkdir()
    _write_json(kai_dir / "settings.json", {"default_model": "gpt-4"})

    with patch("kai_code.rich_commands.rich_settings") as mock_settings:
        mock_settings.project_root = project_dir
        with patch("kai_code.rich_commands.console"):
            _handle_export_settings("/export-settings")

    # Check default filename was used
    output_file = project_dir / "kai-settings.json"
    assert output_file.exists()
    data = json.loads(output_file.read_text())
    assert data.get("default_model") == "gpt-4"


def test_export_settings_custom_filename(tmp_path: Path) -> None:
    """Test /export-settings with custom filename."""
    # Setup project directory
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    kai_dir = project_dir / ".kai"
    kai_dir.mkdir()
    _write_json(kai_dir / "settings.json", {"default_model": "claude-3"})

    with patch("kai_code.rich_commands.rich_settings") as mock_settings:
        mock_settings.project_root = project_dir
        with patch("kai_code.rich_commands.console"):
            _handle_export_settings("/export-settings my-config.json")

    # Check custom filename was used
    output_file = project_dir / "my-config.json"
    assert output_file.exists()
    data = json.loads(output_file.read_text())
    assert data.get("default_model") == "claude-3"


def test_export_settings_shows_success_message(tmp_path: Path) -> None:
    """Test /export-settings shows success message."""
    # Setup project directory
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    kai_dir = project_dir / ".kai"
    kai_dir.mkdir()
    _write_json(kai_dir / "settings.json", {"default_model": "gpt-4"})

    with patch("kai_code.rich_commands.rich_settings") as mock_settings:
        mock_settings.project_root = project_dir
        with patch("kai_code.rich_commands.console") as mock_console:
            _handle_export_settings("/export-settings")

    # Check success message was printed
    call_args_list = [str(call) for call in mock_console.print.call_args_list]
    success_printed = any("[green]" in call and "Exported" in call for call in call_args_list)
    assert success_printed, f"Expected success message, got: {call_args_list}"


def test_export_settings_empty_settings(tmp_path: Path) -> None:
    """Test /export-settings works with no settings files."""
    # Setup project directory with no settings
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    with patch("kai_code.rich_commands.rich_settings") as mock_settings:
        mock_settings.project_root = project_dir
        with patch("kai_code.rich_commands.console"):
            _handle_export_settings("/export-settings")

    # Check file was created (even if empty)
    output_file = project_dir / "kai-settings.json"
    assert output_file.exists()


# ============================================================
# /import-settings command tests
# ============================================================


def test_import_settings_command_recognized() -> None:
    """Test /import-settings command is recognized."""
    agent = MagicMock()
    with patch("kai_code.rich_commands.rich_settings") as mock_settings:
        mock_settings.project_root = None
        with patch("kai_code.rich_commands.console"):
            result = handle_command("/import-settings", agent)
    # Command should be handled (returns None, not the input)
    assert result is None


def test_import_settings_with_filename(tmp_path: Path) -> None:
    """Test /import-settings with filename imports settings."""
    # Setup project directory and input file
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    input_file = project_dir / "config.json"
    _write_json(input_file, {"default_model": "gpt-4", "permission_mode": "normal"})

    with patch("kai_code.rich_commands.rich_settings") as mock_settings:
        mock_settings.project_root = project_dir
        with patch("kai_code.rich_commands.console"):
            _handle_import_settings("/import-settings config.json")

    # Check settings were imported to project settings
    settings_file = project_dir / ".kai" / "settings.json"
    assert settings_file.exists()
    data = json.loads(settings_file.read_text())
    assert data.get("default_model") == "gpt-4"
    assert data.get("permission_mode") == "normal"


def test_import_settings_with_target_global(tmp_path: Path, monkeypatch) -> None:
    """Test /import-settings with --target global."""
    # Setup project directory and input file
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    input_file = project_dir / "config.json"
    _write_json(input_file, {"default_model": "gpt-4"})

    # Mock home directory for global settings
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    monkeypatch.setenv("HOME", str(fake_home))

    with patch("kai_code.rich_commands.rich_settings") as mock_settings:
        mock_settings.project_root = project_dir
        with patch("kai_code.rich_commands.console"):
            _handle_import_settings("/import-settings config.json --target global")

    # Check settings were imported to global settings
    global_settings = fake_home / ".kai" / "settings.json"
    assert global_settings.exists()
    data = json.loads(global_settings.read_text())
    assert data.get("default_model") == "gpt-4"


def test_import_settings_with_target_local(tmp_path: Path) -> None:
    """Test /import-settings with --target local."""
    # Setup project directory and input file
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    input_file = project_dir / "config.json"
    _write_json(input_file, {"default_model": "gpt-4"})

    with patch("kai_code.rich_commands.rich_settings") as mock_settings:
        mock_settings.project_root = project_dir
        with patch("kai_code.rich_commands.console"):
            _handle_import_settings("/import-settings config.json --target local")

    # Check settings were imported to local settings
    local_settings = project_dir / ".kai" / "settings.local.json"
    assert local_settings.exists()
    data = json.loads(local_settings.read_text())
    assert data.get("default_model") == "gpt-4"


def test_import_settings_with_target_project(tmp_path: Path) -> None:
    """Test /import-settings with explicit --target project."""
    # Setup project directory and input file
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    input_file = project_dir / "config.json"
    _write_json(input_file, {"default_model": "gpt-4"})

    with patch("kai_code.rich_commands.rich_settings") as mock_settings:
        mock_settings.project_root = project_dir
        with patch("kai_code.rich_commands.console"):
            _handle_import_settings("/import-settings config.json --target project")

    # Check settings were imported to project settings
    project_settings = project_dir / ".kai" / "settings.json"
    assert project_settings.exists()
    data = json.loads(project_settings.read_text())
    assert data.get("default_model") == "gpt-4"


def test_import_settings_default_target_is_project(tmp_path: Path) -> None:
    """Test /import-settings defaults to project target."""
    # Setup project directory and input file
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    input_file = project_dir / "config.json"
    _write_json(input_file, {"default_model": "gpt-4"})

    with patch("kai_code.rich_commands.rich_settings") as mock_settings:
        mock_settings.project_root = project_dir
        with patch("kai_code.rich_commands.console"):
            _handle_import_settings("/import-settings config.json")

    # Check settings were imported to project settings (default)
    project_settings = project_dir / ".kai" / "settings.json"
    assert project_settings.exists()


def test_import_settings_shows_success_message(tmp_path: Path) -> None:
    """Test /import-settings shows success message."""
    # Setup project directory and input file
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    input_file = project_dir / "config.json"
    _write_json(input_file, {"default_model": "gpt-4"})

    with patch("kai_code.rich_commands.rich_settings") as mock_settings:
        mock_settings.project_root = project_dir
        with patch("kai_code.rich_commands.console") as mock_console:
            _handle_import_settings("/import-settings config.json")

    # Check success message was printed
    call_args_list = [str(call) for call in mock_console.print.call_args_list]
    success_printed = any("[green]" in call and "Imported" in call for call in call_args_list)
    assert success_printed, f"Expected success message, got: {call_args_list}"


# ============================================================
# Error handling tests
# ============================================================


def test_import_settings_missing_filename_shows_usage(tmp_path: Path) -> None:
    """Test /import-settings without filename shows usage message."""
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    with patch("kai_code.rich_commands.rich_settings") as mock_settings:
        mock_settings.project_root = project_dir
        with patch("kai_code.rich_commands.console") as mock_console:
            _handle_import_settings("/import-settings")

    # Check usage message was printed
    call_args_list = [str(call) for call in mock_console.print.call_args_list]
    usage_printed = any("Usage:" in call for call in call_args_list)
    assert usage_printed, f"Expected usage message, got: {call_args_list}"


def test_import_settings_file_not_found(tmp_path: Path) -> None:
    """Test /import-settings with non-existent file shows error."""
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    with patch("kai_code.rich_commands.rich_settings") as mock_settings:
        mock_settings.project_root = project_dir
        with patch("kai_code.rich_commands.console") as mock_console:
            _handle_import_settings("/import-settings nonexistent.json")

    # Check error message was printed
    call_args_list = [str(call) for call in mock_console.print.call_args_list]
    error_printed = any("[red]" in call and "not found" in call for call in call_args_list)
    assert error_printed, f"Expected 'not found' error, got: {call_args_list}"


def test_import_settings_invalid_json(tmp_path: Path) -> None:
    """Test /import-settings with invalid JSON shows error."""
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    input_file = project_dir / "invalid.json"
    input_file.write_text("{ not valid json }")

    with patch("kai_code.rich_commands.rich_settings") as mock_settings:
        mock_settings.project_root = project_dir
        with patch("kai_code.rich_commands.console") as mock_console:
            _handle_import_settings("/import-settings invalid.json")

    # Check error message was printed
    call_args_list = [str(call) for call in mock_console.print.call_args_list]
    error_printed = any("[red]" in call and "Invalid JSON" in call for call in call_args_list)
    assert error_printed, f"Expected 'Invalid JSON' error, got: {call_args_list}"


def test_import_settings_invalid_target(tmp_path: Path) -> None:
    """Test /import-settings with invalid target shows error."""
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    input_file = project_dir / "config.json"
    _write_json(input_file, {"default_model": "gpt-4"})

    with patch("kai_code.rich_commands.rich_settings") as mock_settings:
        mock_settings.project_root = project_dir
        with patch("kai_code.rich_commands.console") as mock_console:
            _handle_import_settings("/import-settings config.json --target invalid")

    # Check error message was printed
    call_args_list = [str(call) for call in mock_console.print.call_args_list]
    error_printed = any("[red]" in call and "Invalid target" in call for call in call_args_list)
    assert error_printed, f"Expected 'Invalid target' error, got: {call_args_list}"


def test_import_settings_unknown_flag(tmp_path: Path) -> None:
    """Test /import-settings with unknown flag shows error."""
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    input_file = project_dir / "config.json"
    _write_json(input_file, {"default_model": "gpt-4"})

    with patch("kai_code.rich_commands.rich_settings") as mock_settings:
        mock_settings.project_root = project_dir
        with patch("kai_code.rich_commands.console") as mock_console:
            _handle_import_settings("/import-settings config.json --unknown flag")

    # Check error message was printed
    call_args_list = [str(call) for call in mock_console.print.call_args_list]
    error_printed = any("[yellow]" in call and "Unknown flag" in call for call in call_args_list)
    assert error_printed, f"Expected 'Unknown flag' error, got: {call_args_list}"


def test_import_settings_invalid_settings_keys(tmp_path: Path) -> None:
    """Test /import-settings with invalid settings keys shows error."""
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    input_file = project_dir / "config.json"
    _write_json(input_file, {"default_model": "gpt-4", "unknown_key": "value"})

    with patch("kai_code.rich_commands.rich_settings") as mock_settings:
        mock_settings.project_root = project_dir
        with patch("kai_code.rich_commands.console") as mock_console:
            _handle_import_settings("/import-settings config.json")

    # Check error message was printed (validation error from import_settings)
    call_args_list = [str(call) for call in mock_console.print.call_args_list]
    error_printed = any("[red]" in call for call in call_args_list)
    assert error_printed, f"Expected error message, got: {call_args_list}"


def test_import_settings_session_fields_rejected(tmp_path: Path) -> None:
    """Test /import-settings rejects session-specific fields."""
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    input_file = project_dir / "config.json"
    _write_json(input_file, {"default_model": "gpt-4", "last_session": "/path"})

    with patch("kai_code.rich_commands.rich_settings") as mock_settings:
        mock_settings.project_root = project_dir
        with patch("kai_code.rich_commands.console") as mock_console:
            _handle_import_settings("/import-settings config.json")

    # Check error message was printed
    call_args_list = [str(call) for call in mock_console.print.call_args_list]
    error_printed = any("[red]" in call for call in call_args_list)
    assert error_printed, f"Expected error for session field, got: {call_args_list}"


# ============================================================
# Argument parsing tests
# ============================================================


def test_import_settings_quoted_filename(tmp_path: Path) -> None:
    """Test /import-settings handles quoted filenames with spaces."""
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    input_file = project_dir / "my config.json"
    _write_json(input_file, {"default_model": "gpt-4"})

    with patch("kai_code.rich_commands.rich_settings") as mock_settings:
        mock_settings.project_root = project_dir
        with patch("kai_code.rich_commands.console"):
            _handle_import_settings('/import-settings "my config.json"')

    # Check settings were imported
    settings_file = project_dir / ".kai" / "settings.json"
    assert settings_file.exists()
    data = json.loads(settings_file.read_text())
    assert data.get("default_model") == "gpt-4"


def test_import_settings_target_before_filename(tmp_path: Path) -> None:
    """Test /import-settings handles --target flag before filename."""
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    input_file = project_dir / "config.json"
    _write_json(input_file, {"default_model": "gpt-4"})

    with patch("kai_code.rich_commands.rich_settings") as mock_settings:
        mock_settings.project_root = project_dir
        with patch("kai_code.rich_commands.console"):
            _handle_import_settings("/import-settings --target local config.json")

    # Check settings were imported to local settings
    local_settings = project_dir / ".kai" / "settings.local.json"
    assert local_settings.exists()


def test_export_settings_case_insensitive_command() -> None:
    """Test /export-settings command is case insensitive."""
    agent = MagicMock()
    with patch("kai_code.rich_commands.rich_settings") as mock_settings:
        mock_settings.project_root = None
        with patch("kai_code.rich_commands.console"):
            result = handle_command("/EXPORT-SETTINGS", agent)
    # Command should be handled
    assert result is None


def test_import_settings_case_insensitive_command() -> None:
    """Test /import-settings command is case insensitive."""
    agent = MagicMock()
    with patch("kai_code.rich_commands.rich_settings") as mock_settings:
        mock_settings.project_root = None
        with patch("kai_code.rich_commands.console"):
            result = handle_command("/IMPORT-SETTINGS", agent)
    # Command should be handled
    assert result is None


def test_import_settings_target_case_insensitive(tmp_path: Path) -> None:
    """Test /import-settings --target value is case insensitive."""
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    input_file = project_dir / "config.json"
    _write_json(input_file, {"default_model": "gpt-4"})

    with patch("kai_code.rich_commands.rich_settings") as mock_settings:
        mock_settings.project_root = project_dir
        with patch("kai_code.rich_commands.console"):
            _handle_import_settings("/import-settings config.json --target LOCAL")

    # Check settings were imported to local settings
    local_settings = project_dir / ".kai" / "settings.local.json"
    assert local_settings.exists()


def test_import_settings_absolute_path(tmp_path: Path) -> None:
    """Test /import-settings with absolute path."""
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    input_file = tmp_path / "external" / "config.json"
    input_file.parent.mkdir()
    _write_json(input_file, {"default_model": "gpt-4"})

    with patch("kai_code.rich_commands.rich_settings") as mock_settings:
        mock_settings.project_root = project_dir
        with patch("kai_code.rich_commands.console"):
            _handle_import_settings(f"/import-settings {input_file}")

    # Check settings were imported
    settings_file = project_dir / ".kai" / "settings.json"
    assert settings_file.exists()
    data = json.loads(settings_file.read_text())
    assert data.get("default_model") == "gpt-4"


def test_import_settings_too_many_arguments(tmp_path: Path) -> None:
    """Test /import-settings with too many arguments shows error."""
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    input_file = project_dir / "config.json"
    _write_json(input_file, {"default_model": "gpt-4"})

    with patch("kai_code.rich_commands.rich_settings") as mock_settings:
        mock_settings.project_root = project_dir
        with patch("kai_code.rich_commands.console") as mock_console:
            _handle_import_settings("/import-settings config.json extra.json")

    # Check error message was printed
    call_args_list = [str(call) for call in mock_console.print.call_args_list]
    error_printed = any("Too many arguments" in call for call in call_args_list)
    assert error_printed, f"Expected 'Too many arguments' error, got: {call_args_list}"
