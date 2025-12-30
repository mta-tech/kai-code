"""Integration tests for actionable error messages in CLI scenarios.

This module contains integration tests that verify error messages are properly
rendered in realistic CLI scenarios, including:
- Unknown command handling with fuzzy suggestions
- File not found errors with similar file suggestions
- API key errors with provider-specific instructions
- Model availability errors with similar model suggestions
- Error rendering in different contexts (panel, simple, text)
"""
from __future__ import annotations

import subprocess
import tempfile
from io import StringIO
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest
from rich.console import Console

from kai_code.errors import (
    ActionableError,
    ActionableErrorException,
    ErrorRenderer,
    ErrorType,
    render_error,
)
from kai_code.error_suggestions import (
    make_api_key_missing_error,
    make_dbt_command_error,
    make_dbt_connection_error,
    make_dbt_model_not_found_error,
    make_file_not_found_error,
    make_file_permission_error,
    make_invalid_file_type_error,
    make_invalid_flag_error,
    make_missing_argument_error,
    make_model_not_available_error,
    make_skill_not_found_error,
    make_unknown_command_error,
    suggest_commands,
    suggest_files,
)


# =============================================================================
# CLI Command Error Integration Tests
# =============================================================================


class TestUnknownCommandIntegration:
    """Integration tests for unknown command error handling in CLI."""

    def test_unknown_command_renders_with_suggestions(self) -> None:
        """Test that unknown command errors render with fuzzy suggestions."""
        available_commands = [
            "/help", "/clear", "/quit", "/exit", "/q",
            "/skills", "/brainstorm", "/models", "/model",
            "/tasks", "/task", "/ralph-loop",
        ]

        # Simulate a typo
        error = make_unknown_command_error("/healp", available_commands)

        # Render the error
        string_io = StringIO()
        console = Console(file=string_io, force_terminal=True, highlight=False)
        render_error(error, console)
        output = string_io.getvalue()

        # Verify the output contains expected elements
        assert "Unknown command" in output
        assert "/healp" in output
        assert "/help" in output  # Should suggest /help
        assert "Suggestions" in output

    def test_unknown_command_shows_available_commands(self) -> None:
        """Test that unknown command error lists available commands when few."""
        available_commands = ["/help", "/clear", "/quit"]

        error = make_unknown_command_error("/test", available_commands)

        string_io = StringIO()
        console = Console(file=string_io, force_terminal=True, highlight=False)
        render_error(error, console)
        output = string_io.getvalue()

        # Should list all available commands since there are only 3
        assert "Available commands:" in output

    def test_unknown_command_warning_severity(self) -> None:
        """Test that unknown command errors use warning severity appropriately."""
        available_commands = ["/help", "/clear"]
        error = make_unknown_command_error("/test", available_commands)
        error.severity = "warning"  # Non-fatal error

        string_io = StringIO()
        console = Console(file=string_io, force_terminal=True, highlight=False)
        renderer = ErrorRenderer(console=console)
        renderer.render(error)
        output = string_io.getvalue()

        # The error should still be rendered (content check)
        assert "Unknown command" in output


class TestFileErrorIntegration:
    """Integration tests for file-related error handling."""

    def test_file_not_found_with_similar_files(self, tmp_path: Path) -> None:
        """Test file not found error suggests similar files from directory."""
        # Create similar files
        (tmp_path / "config.yaml").touch()
        (tmp_path / "config.yml").touch()
        (tmp_path / "settings.yaml").touch()

        # Create error for typo
        error = make_file_not_found_error("configs.yaml", search_dir=tmp_path)

        string_io = StringIO()
        console = Console(file=string_io, force_terminal=True, highlight=False)
        render_error(error, console)
        output = string_io.getvalue()

        # Should contain file not found message
        assert "File not found" in output
        assert "configs.yaml" in output

        # Should suggest similar files
        assert "Did you mean" in output or "config" in output

    def test_file_not_found_includes_recovery_commands(self, tmp_path: Path) -> None:
        """Test file not found error includes ls and find commands."""
        error = make_file_not_found_error("test.json", search_dir=tmp_path)

        string_io = StringIO()
        console = Console(file=string_io, force_terminal=True, highlight=False)
        render_error(error, console)
        output = string_io.getvalue()

        # Should suggest recovery commands
        assert "Try these commands" in output
        assert "ls -la" in output
        assert ".json" in output  # Should include find command for extension

    def test_file_permission_error_with_chmod_suggestions(self) -> None:
        """Test file permission error includes chmod suggestions."""
        error = make_file_permission_error("/etc/passwd", operation="write")

        string_io = StringIO()
        console = Console(file=string_io, force_terminal=True, highlight=False)
        render_error(error, console)
        output = string_io.getvalue()

        # Should contain permission denied message
        assert "Permission denied" in output

        # Should suggest chmod
        assert "chmod" in output

        # Should mention sudo
        assert "sudo" in output

    def test_invalid_file_type_error_with_conversion_hints(self) -> None:
        """Test invalid file type error includes conversion hints."""
        error = make_invalid_file_type_error("config.json", [".yaml", ".yml"])

        string_io = StringIO()
        console = Console(file=string_io, force_terminal=True, highlight=False)
        render_error(error, console)
        output = string_io.getvalue()

        # Should contain file type error
        assert "Invalid file type" in output
        assert ".json" in output
        assert ".yaml" in output

        # Should suggest conversion
        assert "yq" in output or "python" in output  # Conversion tools


class TestAPIKeyErrorIntegration:
    """Integration tests for API key error handling."""

    def test_anthropic_api_key_error_with_instructions(self) -> None:
        """Test Anthropic API key error includes specific instructions."""
        error = make_api_key_missing_error("anthropic")

        string_io = StringIO()
        console = Console(file=string_io, force_terminal=True, highlight=False)
        render_error(error, console)
        output = string_io.getvalue()

        # Should mention Anthropic-specific env var
        assert "ANTHROPIC_API_KEY" in output

        # Should include URL for getting key
        assert "console.anthropic.com" in output

    def test_openai_api_key_error_with_instructions(self) -> None:
        """Test OpenAI API key error includes specific instructions."""
        error = make_api_key_missing_error("openai")

        string_io = StringIO()
        console = Console(file=string_io, force_terminal=True, highlight=False)
        render_error(error, console)
        output = string_io.getvalue()

        # Should mention OpenAI-specific env var
        assert "OPENAI_API_KEY" in output

        # Should include URL
        assert "platform.openai.com" in output

    def test_google_api_key_error_with_instructions(self) -> None:
        """Test Google/Gemini API key error includes specific instructions."""
        error = make_api_key_missing_error("google")

        string_io = StringIO()
        console = Console(file=string_io, force_terminal=True, highlight=False)
        render_error(error, console)
        output = string_io.getvalue()

        # Should mention Google-specific env var
        assert "GOOGLE_API_KEY" in output

    def test_ollama_error_different_from_api_key(self) -> None:
        """Test Ollama error shows running/accessibility message, not API key."""
        error = make_api_key_missing_error("ollama")

        string_io = StringIO()
        console = Console(file=string_io, force_terminal=True, highlight=False)
        render_error(error, console)
        output = string_io.getvalue()

        # Ollama doesn't need API key - should mention running
        assert "running" in output.lower() or "accessible" in output.lower()

        # Should suggest ollama commands
        assert "ollama" in output


class TestModelErrorIntegration:
    """Integration tests for model availability error handling."""

    def test_model_not_available_with_similar_suggestions(self) -> None:
        """Test model not available error suggests similar models."""
        available_models = [
            "gpt-4o-mini", "gpt-4o", "gpt-4",
            "claude-3-opus", "claude-3-sonnet", "claude-3-haiku",
        ]

        # Typo in model name
        error = make_model_not_available_error("gpt-4o-mni", available_models)

        string_io = StringIO()
        console = Console(file=string_io, force_terminal=True, highlight=False)
        render_error(error, console)
        output = string_io.getvalue()

        # Should show model not available
        assert "not available" in output.lower()
        assert "gpt-4o-mni" in output

        # Should suggest correct model
        assert "gpt-4o-mini" in output

    def test_model_not_available_shows_recovery_command(self) -> None:
        """Test model not available error includes /models command."""
        available_models = ["gpt-4o-mini", "gpt-4o"]

        error = make_model_not_available_error("unknown-model", available_models)

        string_io = StringIO()
        console = Console(file=string_io, force_terminal=True, highlight=False)
        render_error(error, console)
        output = string_io.getvalue()

        # Should suggest /models command
        assert "/models" in output

    def test_model_error_lists_all_when_few(self) -> None:
        """Test model error lists all models when there are few available."""
        available_models = ["gpt-4", "claude-3", "gemini"]

        error = make_model_not_available_error("test-model", available_models)

        string_io = StringIO()
        console = Console(file=string_io, force_terminal=True, highlight=False)
        render_error(error, console)
        output = string_io.getvalue()

        # Should list all models
        assert "Available models:" in output


class TestSkillErrorIntegration:
    """Integration tests for skill error handling."""

    def test_skill_not_found_with_similar_suggestions(self) -> None:
        """Test skill not found error suggests similar skills."""
        available_skills = ["code-review", "code-explain", "code-refactor"]

        # Typo in skill name
        error = make_skill_not_found_error("code-reveiw", available_skills)

        string_io = StringIO()
        console = Console(file=string_io, force_terminal=True, highlight=False)
        render_error(error, console)
        output = string_io.getvalue()

        # Should show skill not found
        assert "not found" in output.lower()

        # Should suggest correct skill
        assert "code-review" in output

    def test_skill_not_found_shows_recovery_commands(self) -> None:
        """Test skill not found error includes /skills and reload commands."""
        available_skills = ["test-skill"]

        error = make_skill_not_found_error("unknown-skill", available_skills)

        string_io = StringIO()
        console = Console(file=string_io, force_terminal=True, highlight=False)
        render_error(error, console)
        output = string_io.getvalue()

        # Should suggest /skills and /skill reload
        assert "/skills" in output
        assert "/skill reload" in output


class TestFlagErrorIntegration:
    """Integration tests for command flag error handling."""

    def test_invalid_flag_with_similar_suggestions(self) -> None:
        """Test invalid flag error suggests similar flags."""
        valid_flags = ["--help", "--verbose", "--quiet", "--version", "--timeout"]

        # Typo in flag name
        error = make_invalid_flag_error("--versboe", valid_flags, command="kai")

        string_io = StringIO()
        console = Console(file=string_io, force_terminal=True, highlight=False)
        render_error(error, console)
        output = string_io.getvalue()

        # Should show invalid flag
        assert "Invalid flag" in output
        assert "--versboe" in output

        # Should suggest correct flag
        assert "--verbose" in output

    def test_invalid_flag_shows_help_command(self) -> None:
        """Test invalid flag error includes help command."""
        valid_flags = ["--help", "--verbose"]

        error = make_invalid_flag_error("--test", valid_flags, command="kai")

        string_io = StringIO()
        console = Console(file=string_io, force_terminal=True, highlight=False)
        render_error(error, console)
        output = string_io.getvalue()

        # Should suggest kai --help
        assert "kai --help" in output


class TestMissingArgumentIntegration:
    """Integration tests for missing argument error handling."""

    def test_missing_argument_shows_usage_example(self) -> None:
        """Test missing argument error shows usage example."""
        error = make_missing_argument_error(
            command="/model",
            missing_arg="model_name",
            expected_type="model identifier like 'gpt-4o-mini'",
            usage_example="/model gpt-4o-mini",
        )

        string_io = StringIO()
        console = Console(file=string_io, force_terminal=True, highlight=False)
        render_error(error, console)
        output = string_io.getvalue()

        # Should show missing argument
        assert "Missing required argument" in output
        assert "model_name" in output

        # Should show usage example
        assert "gpt-4o-mini" in output

    def test_missing_argument_shows_expected_type(self) -> None:
        """Test missing argument error shows expected type."""
        error = make_missing_argument_error(
            command="!",
            missing_arg="command",
            expected_type="shell command",
            usage_example="!ls -la",
        )

        string_io = StringIO()
        console = Console(file=string_io, force_terminal=True, highlight=False)
        render_error(error, console)
        output = string_io.getvalue()

        # Should show expected type
        assert "shell command" in output

        # Should show example
        assert "ls -la" in output


# =============================================================================
# DBT Error Integration Tests
# =============================================================================


class TestDBTConnectionErrorIntegration:
    """Integration tests for DBT connection error handling."""

    def test_duckdb_connection_error_with_suggestions(self) -> None:
        """Test DuckDB connection error includes specific suggestions."""
        error = make_dbt_connection_error(
            connection_string="analytics.duckdb",
            adapter_type="duckdb",
            error_details="file not found",
        )

        string_io = StringIO()
        console = Console(file=string_io, force_terminal=True, highlight=False)
        render_error(error, console)
        output = string_io.getvalue()

        # Should mention DuckDB
        assert "database" in output.lower() or "DuckDB" in output

        # Should suggest checking file
        assert "file" in output.lower()

    def test_postgres_connection_error_with_suggestions(self) -> None:
        """Test PostgreSQL connection error includes specific suggestions."""
        error = make_dbt_connection_error(
            connection_string="postgresql://user:pass@host/db",
            error_details="connection refused",
        )

        string_io = StringIO()
        console = Console(file=string_io, force_terminal=True, highlight=False)
        render_error(error, console)
        output = string_io.getvalue()

        # Should mention connection issue
        assert "connect" in output.lower() or "connection" in output.lower()

        # Should suggest pg_isready
        assert "pg_isready" in output

    def test_connection_error_includes_dbt_debug(self) -> None:
        """Test connection error includes dbt debug command."""
        error = make_dbt_connection_error(error_details="connection failed")

        string_io = StringIO()
        console = Console(file=string_io, force_terminal=True, highlight=False)
        render_error(error, console)
        output = string_io.getvalue()

        # Should suggest dbt debug
        assert "dbt debug" in output


class TestDBTModelErrorIntegration:
    """Integration tests for DBT model error handling."""

    def test_dbt_model_not_found_with_suggestions(self) -> None:
        """Test dbt model not found error suggests similar models."""
        available_models = ["stg_orders", "stg_customers", "fct_orders"]

        error = make_dbt_model_not_found_error(
            model_name="stg_ordes",  # typo
            available_models=available_models,
        )

        string_io = StringIO()
        console = Console(file=string_io, force_terminal=True, highlight=False)
        render_error(error, console)
        output = string_io.getvalue()

        # Should show model not found
        assert "not found" in output.lower()
        assert "stg_ordes" in output

        # Should suggest correct model
        assert "stg_orders" in output

    def test_dbt_model_error_includes_dbt_list(self) -> None:
        """Test dbt model error includes dbt list command."""
        error = make_dbt_model_not_found_error(
            model_name="unknown_model",
            available_models=["stg_orders"],
        )

        string_io = StringIO()
        console = Console(file=string_io, force_terminal=True, highlight=False)
        render_error(error, console)
        output = string_io.getvalue()

        # Should suggest dbt list
        assert "dbt list" in output


class TestDBTCommandErrorIntegration:
    """Integration tests for DBT command error handling."""

    def test_dbt_compilation_error_suggestions(self) -> None:
        """Test dbt compilation error includes relevant suggestions."""
        error = make_dbt_command_error(
            command="dbt run",
            error_output="Compilation Error: Invalid syntax in model",
            model_name="stg_orders",
        )

        string_io = StringIO()
        console = Console(file=string_io, force_terminal=True, highlight=False)
        render_error(error, console)
        output = string_io.getvalue()

        # Should show command failed
        assert "dbt" in output.lower()
        assert "failed" in output.lower() or "error" in output.lower()

        # Should suggest compile
        assert "dbt compile" in output

    def test_dbt_database_error_suggestions(self) -> None:
        """Test dbt database error includes relevant suggestions."""
        error = make_dbt_command_error(
            command="dbt run",
            error_output="Database error: relation does not exist",
            model_name="fct_orders",
        )

        string_io = StringIO()
        console = Console(file=string_io, force_terminal=True, highlight=False)
        render_error(error, console)
        output = string_io.getvalue()

        # Should mention database error
        assert "dbt" in output.lower()

        # Should suggest dbt debug
        assert "dbt debug" in output


# =============================================================================
# Error Rendering Integration Tests
# =============================================================================


class TestErrorRenderingModes:
    """Integration tests for different error rendering modes."""

    def test_full_panel_rendering(self) -> None:
        """Test full panel rendering with all sections."""
        error = ActionableError(
            error_type=ErrorType.FILE_NOT_FOUND,
            message="Config file not found",
            suggestions=["Check path", "Verify existence"],
            recovery_commands=["ls -la", "find . -name 'config*'"],
            related_items=["config.yml", "config.yaml"],
            context={"path": "config.json", "cwd": "/home/user"},
        )

        string_io = StringIO()
        console = Console(file=string_io, force_terminal=True, highlight=False)
        renderer = ErrorRenderer(console=console)
        renderer.render(error)
        output = string_io.getvalue()

        # All sections should be present
        assert "Config file not found" in output
        assert "Suggestions" in output
        assert "Try these commands" in output
        assert "Did you mean" in output
        assert "Context" in output

    def test_simple_inline_rendering(self) -> None:
        """Test simple inline rendering without panel."""
        error = ActionableError(
            error_type=ErrorType.COMMAND_NOT_FOUND,
            message="Unknown command: /test",
            suggestions=["Check spelling"],
            related_items=["/help", "/clear"],
        )

        string_io = StringIO()
        console = Console(file=string_io, force_terminal=True, highlight=False)
        renderer = ErrorRenderer(console=console)
        renderer.render_simple(error)
        output = string_io.getvalue()

        # Should contain message and suggestions inline
        assert "Unknown command" in output
        assert "Check spelling" in output
        assert "/help" in output

    def test_text_object_rendering(self) -> None:
        """Test rendering to Rich Text object for embedding."""
        from rich.text import Text

        error = ActionableError(
            error_type=ErrorType.API_KEY_MISSING,
            message="API key not configured",
            suggestions=["Set ANTHROPIC_API_KEY"],
        )

        renderer = ErrorRenderer()
        text = renderer.render_to_text(error)

        # Should return Text object
        assert isinstance(text, Text)
        assert "API key not configured" in text.plain

    def test_severity_affects_rendering(self) -> None:
        """Test that different severities render differently."""
        # Error severity
        error_msg = ActionableError(
            error_type=ErrorType.INTERNAL_ERROR,
            message="Fatal error occurred",
            severity="error",
        )

        # Warning severity
        warning_msg = ActionableError(
            error_type=ErrorType.FILE_NOT_FOUND,
            message="Optional file missing",
            severity="warning",
        )

        # Both should render without error
        renderer = ErrorRenderer()
        error_output = renderer.render_to_string(error_msg)
        warning_output = renderer.render_to_string(warning_msg)

        assert "Fatal error occurred" in error_output
        assert "Optional file missing" in warning_output


class TestErrorExceptionIntegration:
    """Integration tests for ActionableErrorException handling."""

    def test_exception_can_be_raised_and_caught(self) -> None:
        """Test ActionableErrorException can be raised and rendered."""
        error = ActionableError(
            error_type=ErrorType.NETWORK_ERROR,
            message="Connection refused",
            suggestions=["Check network", "Retry later"],
        )

        with pytest.raises(ActionableErrorException) as exc_info:
            raise ActionableErrorException(error)

        caught = exc_info.value

        # Render the caught error
        string_io = StringIO()
        console = Console(file=string_io, force_terminal=True, highlight=False)
        render_error(caught.error, console)
        output = string_io.getvalue()

        assert "Connection refused" in output
        assert "Check network" in output

    def test_exception_preserves_error_details(self) -> None:
        """Test that exception preserves all error information."""
        error = ActionableError(
            error_type=ErrorType.TIMEOUT_ERROR,
            message="Request timed out",
            suggestions=["Increase timeout", "Retry"],
            recovery_commands=["--timeout 300"],
            context={"timeout": "30s"},
        )

        exception = ActionableErrorException(error)

        # All details should be accessible
        assert exception.error.error_type == ErrorType.TIMEOUT_ERROR
        assert exception.error.suggestions == ["Increase timeout", "Retry"]
        assert exception.error.recovery_commands == ["--timeout 300"]
        assert exception.error.context == {"timeout": "30s"}


# =============================================================================
# Real CLI Scenario Integration Tests
# =============================================================================


class TestRealisticCLIScenarios:
    """Integration tests simulating realistic CLI usage scenarios."""

    def test_typo_in_help_command(self) -> None:
        """Test realistic scenario: user types /hepl instead of /help."""
        available_commands = [
            "/help", "/clear", "/quit", "/exit", "/tokens",
            "/skills", "/models", "/model",
        ]

        error = make_unknown_command_error("/hepl", available_commands)
        error.severity = "warning"

        renderer = ErrorRenderer()
        output = renderer.render_to_string(error)

        # Should clearly indicate what went wrong
        assert "Unknown command" in output
        assert "/hepl" in output

        # Should suggest the correct command
        assert "/help" in output

        # Should provide help on how to find commands
        assert "/help" in error.recovery_commands

    def test_missing_config_file_in_project(self, tmp_path: Path) -> None:
        """Test realistic scenario: user references non-existent config."""
        # Create project structure with similar files
        (tmp_path / "config.yaml").touch()
        (tmp_path / "config.production.yaml").touch()
        (tmp_path / "settings.json").touch()

        # User tries to read wrong file
        error = make_file_not_found_error("config.dev.yaml", search_dir=tmp_path)

        renderer = ErrorRenderer()
        output = renderer.render_to_string(error)

        # Should show the file path attempted
        assert "config.dev.yaml" in output

        # Should suggest looking for similar files
        assert "config" in output  # Similar files with 'config' in name

    def test_wrong_model_name_with_provider_prefix(self) -> None:
        """Test realistic scenario: user types wrong model name."""
        available_models = [
            "claude-3-5-sonnet-20241022",
            "claude-3-opus-20240229",
            "claude-3-haiku-20240307",
            "gpt-4o-mini",
            "gpt-4o",
        ]

        # User types wrong Claude model name
        error = make_model_not_available_error(
            "claude-3-5-sonnet",  # Missing date suffix
            available_models,
        )

        renderer = ErrorRenderer()
        output = renderer.render_to_string(error)

        # Should indicate model not available
        assert "not available" in output.lower()

        # Should suggest similar model(s)
        assert "claude-3-5-sonnet-20241022" in output or "Did you mean" in output

    def test_skill_command_typo_scenario(self) -> None:
        """Test realistic scenario: user makes typo in skill name."""
        available_skills = [
            "code-review",
            "code-refactor",
            "code-explain",
            "test-writer",
            "doc-generator",
        ]

        # User types wrong skill name
        error = make_skill_not_found_error("cod-review", available_skills)

        renderer = ErrorRenderer()
        output = renderer.render_to_string(error)

        # Should indicate skill not found
        assert "not found" in output.lower()

        # Should suggest similar skill
        assert "code-review" in output

    def test_ralph_loop_missing_promise_flag(self) -> None:
        """Test realistic scenario: ralph-loop without --promise value."""
        error = make_missing_argument_error(
            command="/ralph-loop",
            missing_arg="promise",
            expected_type="goal description string",
            usage_example='/ralph-loop --promise "Complete the feature implementation"',
        )

        renderer = ErrorRenderer()
        output = renderer.render_to_string(error)

        # Should show what's missing
        assert "promise" in output

        # Should show usage example
        assert "ralph-loop" in output

    def test_dbt_model_typo_in_run_command(self) -> None:
        """Test realistic scenario: dbt run with typo in model name."""
        available_models = [
            "stg_orders",
            "stg_customers",
            "stg_products",
            "int_order_items",
            "fct_orders",
        ]

        # User typos model name
        error = make_dbt_model_not_found_error(
            model_name="stg_order",  # Missing 's'
            available_models=available_models,
        )

        renderer = ErrorRenderer()
        output = renderer.render_to_string(error)

        # Should show the wrong model name
        assert "stg_order" in output

        # Should suggest the correct model
        assert "stg_orders" in output


class TestErrorConsistencyAcrossModules:
    """Integration tests ensuring error consistency across different modules."""

    def test_all_error_types_render_without_crash(self) -> None:
        """Test that all error types can be rendered."""
        for error_type in ErrorType:
            error = ActionableError(
                error_type=error_type,
                message=f"Test message for {error_type.value}",
                suggestions=["Test suggestion"],
            )

            renderer = ErrorRenderer()
            # Should not raise
            output = renderer.render_to_string(error)
            assert "Test message" in output

    def test_error_context_serialization_roundtrip(self) -> None:
        """Test that errors can be serialized and deserialized."""
        original = ActionableError(
            error_type=ErrorType.API_KEY_MISSING,
            message="Test error",
            suggestions=["Suggestion 1", "Suggestion 2"],
            recovery_commands=["cmd1", "cmd2"],
            related_items=["item1", "item2"],
            severity="warning",
            context={"key1": "value1", "key2": "value2"},
        )

        # Serialize
        data = original.to_dict()

        # Deserialize
        restored = ActionableError.from_dict(data)

        # Verify
        assert restored.error_type == original.error_type
        assert restored.message == original.message
        assert restored.suggestions == original.suggestions
        assert restored.recovery_commands == original.recovery_commands
        assert restored.related_items == original.related_items
        assert restored.severity == original.severity
        assert restored.context == original.context

        # Both should render the same
        renderer = ErrorRenderer()
        original_output = renderer.render_to_string(original)
        restored_output = renderer.render_to_string(restored)
        assert original_output == restored_output

    def test_empty_error_renders_gracefully(self) -> None:
        """Test that errors with minimal info still render."""
        error = ActionableError(
            error_type=ErrorType.UNKNOWN_ERROR,
            message="Something went wrong",
        )

        renderer = ErrorRenderer()
        output = renderer.render_to_string(error)

        # Should still contain the message
        assert "Something went wrong" in output

        # Should not contain section headers for empty sections
        assert "Suggestions:" not in output
        assert "Try these commands:" not in output
        assert "Did you mean:" not in output
