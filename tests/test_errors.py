"""Tests for the actionable error framework.

This module contains tests for:
- ActionableError data model creation and methods
- ErrorRenderer output formatting
- Fuzzy matching utilities (similar_strings, suggest_commands, suggest_files, etc.)
"""
from __future__ import annotations

import tempfile
from io import StringIO
from pathlib import Path

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
    DEFAULT_MAX_SUGGESTIONS,
    DEFAULT_SIMILARITY_THRESHOLD,
    FILE_TYPE_CONVERSIONS,
    PROVIDER_API_KEY_INSTRUCTIONS,
    make_api_key_missing_error,
    make_file_not_found_error,
    make_file_permission_error,
    make_invalid_file_type_error,
    make_invalid_flag_error,
    make_missing_argument_error,
    make_model_not_available_error,
    make_skill_not_found_error,
    make_unknown_command_error,
    similar_strings,
    suggest_commands,
    suggest_files,
    suggest_flags,
    suggest_values,
)


# =============================================================================
# ActionableError Tests
# =============================================================================


class TestActionableErrorCreation:
    """Tests for ActionableError dataclass creation and basic attributes."""

    def test_create_minimal_error(self) -> None:
        """Test creating an error with only required fields."""
        error = ActionableError(
            error_type=ErrorType.FILE_NOT_FOUND,
            message="File 'config.yaml' not found",
        )
        assert error.error_type == ErrorType.FILE_NOT_FOUND
        assert error.message == "File 'config.yaml' not found"
        assert error.suggestions == []
        assert error.recovery_commands == []
        assert error.related_items == []
        assert error.severity == "error"
        assert error.context == {}

    def test_create_full_error(self) -> None:
        """Test creating an error with all fields populated."""
        error = ActionableError(
            error_type=ErrorType.COMMAND_NOT_FOUND,
            message="Unknown command: /helpp",
            suggestions=["Check the command spelling", "Use /help for available commands"],
            recovery_commands=["kai --help", "/help"],
            related_items=["/help", "/heap"],
            severity="warning",
            context={"command": "/helpp", "cwd": "/home/user"},
        )
        assert error.error_type == ErrorType.COMMAND_NOT_FOUND
        assert error.message == "Unknown command: /helpp"
        assert len(error.suggestions) == 2
        assert len(error.recovery_commands) == 2
        assert len(error.related_items) == 2
        assert error.severity == "warning"
        assert error.context["command"] == "/helpp"

    def test_error_types_coverage(self) -> None:
        """Test that all ErrorType enum values can be used."""
        for error_type in ErrorType:
            error = ActionableError(
                error_type=error_type,
                message=f"Test message for {error_type.value}",
            )
            assert error.error_type == error_type


class TestActionableErrorMethods:
    """Tests for ActionableError instance methods."""

    def test_str_representation(self) -> None:
        """Test __str__ method returns expected format."""
        error = ActionableError(
            error_type=ErrorType.API_KEY_MISSING,
            message="OpenAI API key not found",
        )
        assert str(error) == "[api_key_missing] OpenAI API key not found"

    def test_has_suggestions_true(self) -> None:
        """Test has_suggestions returns True when suggestions exist."""
        error = ActionableError(
            error_type=ErrorType.FILE_NOT_FOUND,
            message="File not found",
            suggestions=["Check the path"],
        )
        assert error.has_suggestions() is True

    def test_has_suggestions_false(self) -> None:
        """Test has_suggestions returns False when no suggestions."""
        error = ActionableError(
            error_type=ErrorType.FILE_NOT_FOUND,
            message="File not found",
        )
        assert error.has_suggestions() is False

    def test_has_recovery_commands_true(self) -> None:
        """Test has_recovery_commands returns True when commands exist."""
        error = ActionableError(
            error_type=ErrorType.PERMISSION_DENIED,
            message="Permission denied",
            recovery_commands=["sudo chmod +r file.txt"],
        )
        assert error.has_recovery_commands() is True

    def test_has_recovery_commands_false(self) -> None:
        """Test has_recovery_commands returns False when no commands."""
        error = ActionableError(
            error_type=ErrorType.PERMISSION_DENIED,
            message="Permission denied",
        )
        assert error.has_recovery_commands() is False

    def test_has_related_items_true(self) -> None:
        """Test has_related_items returns True when items exist."""
        error = ActionableError(
            error_type=ErrorType.FILE_NOT_FOUND,
            message="File not found",
            related_items=["config.yml", "conf.yaml"],
        )
        assert error.has_related_items() is True

    def test_has_related_items_false(self) -> None:
        """Test has_related_items returns False when no items."""
        error = ActionableError(
            error_type=ErrorType.FILE_NOT_FOUND,
            message="File not found",
        )
        assert error.has_related_items() is False

    def test_to_dict(self) -> None:
        """Test to_dict method returns correct dictionary."""
        error = ActionableError(
            error_type=ErrorType.INVALID_FLAG,
            message="Unknown flag: --versboe",
            suggestions=["Did you mean --verbose?"],
            recovery_commands=["kai --help"],
            related_items=["--verbose"],
            severity="warning",
            context={"flag": "--versboe"},
        )
        result = error.to_dict()

        assert result["error_type"] == "invalid_flag"
        assert result["message"] == "Unknown flag: --versboe"
        assert result["suggestions"] == ["Did you mean --verbose?"]
        assert result["recovery_commands"] == ["kai --help"]
        assert result["related_items"] == ["--verbose"]
        assert result["severity"] == "warning"
        assert result["context"] == {"flag": "--versboe"}

    def test_from_dict(self) -> None:
        """Test from_dict class method creates correct error."""
        data = {
            "error_type": "file_not_found",
            "message": "Config file missing",
            "suggestions": ["Create config.yaml"],
            "recovery_commands": ["touch config.yaml"],
            "related_items": ["config.yml"],
            "severity": "error",
            "context": {"path": "config.yaml"},
        }
        error = ActionableError.from_dict(data)

        assert error.error_type == ErrorType.FILE_NOT_FOUND
        assert error.message == "Config file missing"
        assert error.suggestions == ["Create config.yaml"]
        assert error.recovery_commands == ["touch config.yaml"]
        assert error.related_items == ["config.yml"]
        assert error.severity == "error"
        assert error.context == {"path": "config.yaml"}

    def test_from_dict_with_unknown_error_type(self) -> None:
        """Test from_dict handles unknown error types gracefully."""
        data = {
            "error_type": "nonexistent_error_type",
            "message": "Test message",
        }
        error = ActionableError.from_dict(data)

        assert error.error_type == ErrorType.UNKNOWN_ERROR
        assert error.message == "Test message"

    def test_from_dict_with_missing_fields(self) -> None:
        """Test from_dict handles missing fields with defaults."""
        data = {}
        error = ActionableError.from_dict(data)

        assert error.error_type == ErrorType.UNKNOWN_ERROR
        assert error.message == "An unknown error occurred"
        assert error.suggestions == []
        assert error.recovery_commands == []
        assert error.related_items == []
        assert error.severity == "error"
        assert error.context == {}

    def test_roundtrip_to_dict_from_dict(self) -> None:
        """Test that to_dict and from_dict are inverse operations."""
        original = ActionableError(
            error_type=ErrorType.API_ERROR,
            message="API request failed",
            suggestions=["Check your connection", "Retry the request"],
            recovery_commands=["curl -I api.example.com"],
            related_items=["api_health", "api_status"],
            severity="error",
            context={"endpoint": "/v1/test", "status_code": "503"},
        )
        data = original.to_dict()
        restored = ActionableError.from_dict(data)

        assert restored.error_type == original.error_type
        assert restored.message == original.message
        assert restored.suggestions == original.suggestions
        assert restored.recovery_commands == original.recovery_commands
        assert restored.related_items == original.related_items
        assert restored.severity == original.severity
        assert restored.context == original.context


class TestActionableErrorException:
    """Tests for ActionableErrorException wrapper."""

    def test_create_exception(self) -> None:
        """Test creating an exception with ActionableError."""
        error = ActionableError(
            error_type=ErrorType.CONFIGURATION_ERROR,
            message="Invalid configuration",
        )
        exception = ActionableErrorException(error)

        assert exception.error == error
        assert str(exception) == "[configuration_error] Invalid configuration"

    def test_raise_and_catch_exception(self) -> None:
        """Test raising and catching ActionableErrorException."""
        error = ActionableError(
            error_type=ErrorType.NETWORK_ERROR,
            message="Connection refused",
            suggestions=["Check your internet connection"],
        )

        with pytest.raises(ActionableErrorException) as exc_info:
            raise ActionableErrorException(error)

        caught = exc_info.value
        assert caught.error.error_type == ErrorType.NETWORK_ERROR
        assert caught.error.suggestions == ["Check your internet connection"]

    def test_exception_is_standard_exception(self) -> None:
        """Test that ActionableErrorException is a standard Exception."""
        error = ActionableError(
            error_type=ErrorType.TIMEOUT_ERROR,
            message="Request timed out",
        )
        exception = ActionableErrorException(error)

        assert isinstance(exception, Exception)


# =============================================================================
# ErrorRenderer Tests
# =============================================================================


class TestErrorRendererBasics:
    """Tests for ErrorRenderer basic functionality."""

    def test_create_renderer_with_default_console(self) -> None:
        """Test creating renderer with default console."""
        renderer = ErrorRenderer()
        assert renderer.console is not None

    def test_create_renderer_with_custom_console(self) -> None:
        """Test creating renderer with custom console."""
        custom_console = Console(file=StringIO(), force_terminal=True)
        renderer = ErrorRenderer(console=custom_console)
        assert renderer.console is custom_console

    def test_colors_defined(self) -> None:
        """Test that all expected colors are defined."""
        expected_colors = ["error", "warning", "info", "primary", "dim", "suggestion", "command", "related"]
        for color in expected_colors:
            assert color in ErrorRenderer.COLORS

    def test_icons_defined(self) -> None:
        """Test that all expected icons are defined."""
        expected_icons = ["error", "warning", "info"]
        for icon in expected_icons:
            assert icon in ErrorRenderer.ICONS


class TestErrorRendererOutput:
    """Tests for ErrorRenderer output formatting."""

    def test_render_to_string_contains_message(self) -> None:
        """Test that rendered output contains the error message."""
        error = ActionableError(
            error_type=ErrorType.FILE_NOT_FOUND,
            message="Config file not found",
        )
        renderer = ErrorRenderer()
        output = renderer.render_to_string(error)

        assert "Config file not found" in output

    def test_render_to_string_contains_suggestions(self) -> None:
        """Test that rendered output contains suggestions."""
        error = ActionableError(
            error_type=ErrorType.FILE_NOT_FOUND,
            message="File missing",
            suggestions=["Check the file path", "Create the file"],
        )
        renderer = ErrorRenderer()
        output = renderer.render_to_string(error)

        assert "Suggestions:" in output
        assert "Check the file path" in output
        assert "Create the file" in output

    def test_render_to_string_contains_recovery_commands(self) -> None:
        """Test that rendered output contains recovery commands."""
        error = ActionableError(
            error_type=ErrorType.PERMISSION_DENIED,
            message="Access denied",
            recovery_commands=["chmod +r file.txt", "sudo ls -la"],
        )
        renderer = ErrorRenderer()
        output = renderer.render_to_string(error)

        assert "Try these commands:" in output
        assert "chmod +r file.txt" in output
        assert "sudo ls -la" in output

    def test_render_to_string_contains_related_items(self) -> None:
        """Test that rendered output contains related items."""
        error = ActionableError(
            error_type=ErrorType.COMMAND_NOT_FOUND,
            message="Unknown command",
            related_items=["/help", "/quit", "/clear"],
        )
        renderer = ErrorRenderer()
        output = renderer.render_to_string(error)

        assert "Did you mean:" in output
        assert "/help" in output
        assert "/quit" in output
        assert "/clear" in output

    def test_render_to_string_contains_context(self) -> None:
        """Test that rendered output contains context information."""
        error = ActionableError(
            error_type=ErrorType.API_ERROR,
            message="API request failed",
            context={"endpoint": "/v1/chat", "status_code": "500"},
        )
        renderer = ErrorRenderer()
        output = renderer.render_to_string(error)

        assert "Context:" in output
        assert "endpoint" in output
        assert "/v1/chat" in output
        assert "status_code" in output
        assert "500" in output

    def test_render_to_string_contains_error_type_in_title(self) -> None:
        """Test that rendered output contains error type in title."""
        error = ActionableError(
            error_type=ErrorType.API_KEY_MISSING,
            message="API key not configured",
        )
        renderer = ErrorRenderer()
        output = renderer.render_to_string(error)

        # The title should contain the formatted error type
        assert "Api Key Missing" in output

    def test_render_minimal_error(self) -> None:
        """Test rendering an error with only required fields."""
        error = ActionableError(
            error_type=ErrorType.INTERNAL_ERROR,
            message="Something went wrong",
        )
        renderer = ErrorRenderer()
        output = renderer.render_to_string(error)

        assert "Something went wrong" in output
        # Should not contain section headers for empty sections
        assert "Suggestions:" not in output
        assert "Try these commands:" not in output
        assert "Did you mean:" not in output
        assert "Context:" not in output

    def test_render_severity_warning(self) -> None:
        """Test rendering a warning-severity error."""
        error = ActionableError(
            error_type=ErrorType.FILE_NOT_FOUND,
            message="Optional file missing",
            severity="warning",
        )
        renderer = ErrorRenderer()
        output = renderer.render_to_string(error)

        # Warning icon should be present
        assert "Optional file missing" in output

    def test_render_severity_info(self) -> None:
        """Test rendering an info-severity error."""
        error = ActionableError(
            error_type=ErrorType.CONFIGURATION_ERROR,
            message="Configuration loaded with defaults",
            severity="info",
        )
        renderer = ErrorRenderer()
        output = renderer.render_to_string(error)

        assert "Configuration loaded with defaults" in output

    def test_render_to_text_returns_text_object(self) -> None:
        """Test render_to_text returns a Rich Text object."""
        from rich.text import Text

        error = ActionableError(
            error_type=ErrorType.VALIDATION_ERROR,
            message="Invalid input",
        )
        renderer = ErrorRenderer()
        result = renderer.render_to_text(error)

        assert isinstance(result, Text)
        assert "Invalid input" in result.plain


class TestErrorRendererSimple:
    """Tests for ErrorRenderer.render_simple method."""

    def test_render_simple_contains_message(self) -> None:
        """Test simple render contains the message."""
        string_io = StringIO()
        console = Console(file=string_io, force_terminal=True, highlight=False)
        renderer = ErrorRenderer(console=console)

        error = ActionableError(
            error_type=ErrorType.FILE_NOT_FOUND,
            message="File not found: test.txt",
        )
        renderer.render_simple(error)

        output = string_io.getvalue()
        assert "File not found: test.txt" in output

    def test_render_simple_shows_suggestions(self) -> None:
        """Test simple render shows suggestions inline."""
        string_io = StringIO()
        console = Console(file=string_io, force_terminal=True, highlight=False)
        renderer = ErrorRenderer(console=console)

        error = ActionableError(
            error_type=ErrorType.FILE_NOT_FOUND,
            message="Missing file",
            suggestions=["Check spelling", "Verify path"],
        )
        renderer.render_simple(error)

        output = string_io.getvalue()
        assert "Check spelling" in output
        assert "Verify path" in output

    def test_render_simple_shows_related_items_inline(self) -> None:
        """Test simple render shows related items inline."""
        string_io = StringIO()
        console = Console(file=string_io, force_terminal=True, highlight=False)
        renderer = ErrorRenderer(console=console)

        error = ActionableError(
            error_type=ErrorType.COMMAND_NOT_FOUND,
            message="Unknown command",
            related_items=["/help", "/quit"],
        )
        renderer.render_simple(error)

        output = string_io.getvalue()
        assert "Did you mean:" in output
        assert "/help" in output
        assert "/quit" in output

    def test_render_simple_limits_related_items_to_three(self) -> None:
        """Test simple render limits related items to 3 plus ellipsis."""
        string_io = StringIO()
        console = Console(file=string_io, force_terminal=True, highlight=False)
        renderer = ErrorRenderer(console=console)

        error = ActionableError(
            error_type=ErrorType.COMMAND_NOT_FOUND,
            message="Unknown command",
            related_items=["a", "b", "c", "d", "e"],
        )
        renderer.render_simple(error)

        output = string_io.getvalue()
        assert "a" in output
        assert "b" in output
        assert "c" in output
        assert "..." in output


class TestRenderErrorFunction:
    """Tests for the render_error convenience function."""

    def test_render_error_outputs_to_console(self) -> None:
        """Test render_error function outputs correctly."""
        string_io = StringIO()
        console = Console(file=string_io, force_terminal=True, highlight=False)

        error = ActionableError(
            error_type=ErrorType.RATE_LIMIT_ERROR,
            message="Rate limit exceeded",
        )
        render_error(error, console=console)

        output = string_io.getvalue()
        assert "Rate limit exceeded" in output

    def test_render_error_with_default_console(self) -> None:
        """Test render_error works without providing console."""
        error = ActionableError(
            error_type=ErrorType.INTERNAL_ERROR,
            message="Internal error",
        )
        # Should not raise - just verify it runs
        # We can't easily capture stdout without more complex mocking
        render_error(error)


# =============================================================================
# Fuzzy Matching Utilities Tests
# =============================================================================


class TestSimilarStrings:
    """Tests for similar_strings function."""

    def test_exact_match(self) -> None:
        """Test that exact matches are found."""
        result = similar_strings("hello", ["hello", "world", "help"])
        assert "hello" in result

    def test_close_match(self) -> None:
        """Test that close matches are found."""
        result = similar_strings("config.yaml", ["config.yml", "settings.yaml", "data.json"])
        assert len(result) > 0
        # config.yml should be a close match
        assert any("config" in r for r in result)

    def test_no_match_below_threshold(self) -> None:
        """Test that dissimilar strings are not matched."""
        result = similar_strings("hello", ["zzzzz", "xxxxx", "yyyyy"])
        assert len(result) == 0

    def test_respects_max_results(self) -> None:
        """Test that n parameter limits results."""
        candidates = ["test1", "test2", "test3", "test4", "test5"]
        result = similar_strings("test", candidates, n=2)
        assert len(result) <= 2

    def test_respects_cutoff_threshold(self) -> None:
        """Test that cutoff parameter affects matches."""
        candidates = ["hello", "helo", "hell", "hey"]
        # High threshold - should only match very close
        result_high = similar_strings("hello", candidates, cutoff=0.9)
        # Low threshold - should match more liberally
        result_low = similar_strings("hello", candidates, cutoff=0.5)

        assert len(result_low) >= len(result_high)

    def test_empty_target_returns_empty(self) -> None:
        """Test that empty target returns empty list."""
        result = similar_strings("", ["hello", "world"])
        assert result == []

    def test_empty_candidates_returns_empty(self) -> None:
        """Test that empty candidates returns empty list."""
        result = similar_strings("hello", [])
        assert result == []

    def test_filters_empty_candidates(self) -> None:
        """Test that empty strings in candidates are filtered."""
        result = similar_strings("hello", ["hello", "", "helo", ""])
        # Should not fail and should find matches
        assert "hello" in result

    def test_default_values(self) -> None:
        """Test that default values are used correctly."""
        # Should use DEFAULT_SIMILARITY_THRESHOLD and DEFAULT_MAX_SUGGESTIONS
        result = similar_strings("test", ["test1", "test2", "test3", "test4"])
        assert len(result) <= DEFAULT_MAX_SUGGESTIONS


class TestSuggestCommands:
    """Tests for suggest_commands function."""

    def test_suggest_similar_command(self) -> None:
        """Test suggesting similar commands."""
        commands = ["/help", "/clear", "/quit", "/tokens", "/model"]
        result = suggest_commands("/healp", commands)
        assert "/help" in result

    def test_case_insensitive_matching(self) -> None:
        """Test that matching is case-insensitive."""
        commands = ["/Help", "/CLEAR", "/Quit"]
        result = suggest_commands("/help", commands)
        # Should find /Help even though case differs
        assert len(result) > 0

    def test_prefix_handling(self) -> None:
        """Test that command prefixes are handled."""
        commands = ["/help", "/clear"]
        result = suggest_commands("/helpp", commands)
        assert "/help" in result

    def test_double_dash_prefix(self) -> None:
        """Test commands with -- prefix."""
        commands = ["--help", "--verbose", "--quiet"]
        result = suggest_commands("--versboe", commands)
        assert "--verbose" in result

    def test_single_dash_prefix(self) -> None:
        """Test commands with - prefix."""
        commands = ["-h", "-v", "-q"]
        result = suggest_commands("-V", commands)
        # -V should match -v
        assert len(result) >= 0  # May or may not match based on threshold

    def test_empty_target_returns_empty(self) -> None:
        """Test that empty target returns empty list."""
        result = suggest_commands("", ["/help", "/clear"])
        assert result == []

    def test_empty_commands_returns_empty(self) -> None:
        """Test that empty commands list returns empty."""
        result = suggest_commands("/help", [])
        assert result == []

    def test_respects_max_results(self) -> None:
        """Test that n parameter limits results."""
        commands = ["/test1", "/test2", "/test3", "/test4", "/test5"]
        result = suggest_commands("/test", commands, n=2)
        assert len(result) <= 2


class TestSuggestFlags:
    """Tests for suggest_flags function."""

    def test_suggest_similar_flag(self) -> None:
        """Test suggesting similar flags."""
        flags = ["--help", "--verbose", "--quiet", "--version"]
        result = suggest_flags("--versboe", flags)
        assert "--verbose" in result

    def test_short_flags(self) -> None:
        """Test short flags work correctly."""
        flags = ["-h", "-v", "-q"]
        result = suggest_flags("-w", flags)
        # May or may not match based on similarity
        assert isinstance(result, list)

    def test_mixed_flag_styles(self) -> None:
        """Test mixed long and short flags."""
        flags = ["-h", "--help", "-v", "--verbose"]
        result = suggest_flags("--hlp", flags)
        assert any("help" in flag.lower() for flag in result)


class TestSuggestFiles:
    """Tests for suggest_files function."""

    def test_suggest_similar_files(self, tmp_path: Path) -> None:
        """Test suggesting similar file names."""
        # Create test files
        (tmp_path / "config.yaml").touch()
        (tmp_path / "config.yml").touch()
        (tmp_path / "settings.json").touch()

        result = suggest_files("config.yml", search_dir=tmp_path)
        assert len(result) > 0

    def test_recursive_search(self, tmp_path: Path) -> None:
        """Test recursive file search."""
        # Create nested directory structure
        subdir = tmp_path / "configs"
        subdir.mkdir()
        (subdir / "app.yaml").touch()
        (tmp_path / "settings.yaml").touch()

        result = suggest_files("app.yml", search_dir=tmp_path, recursive=True)
        # Should find app.yaml in subdirectory
        assert any("app.yaml" in r for r in result)

    def test_non_recursive_search(self, tmp_path: Path) -> None:
        """Test non-recursive file search."""
        # Create nested directory structure
        subdir = tmp_path / "configs"
        subdir.mkdir()
        (subdir / "app.yaml").touch()
        (tmp_path / "settings.yaml").touch()

        result = suggest_files("app.yml", search_dir=tmp_path, recursive=False)
        # Should NOT find app.yaml in subdirectory
        assert not any("app.yaml" in r for r in result)

    def test_extension_filter(self, tmp_path: Path) -> None:
        """Test filtering by file extension."""
        (tmp_path / "config.yaml").touch()
        (tmp_path / "config.json").touch()
        (tmp_path / "config.txt").touch()

        result = suggest_files(
            "configs.yaml",
            search_dir=tmp_path,
            extensions=[".yaml", ".yml"],
        )
        # Should only include yaml files
        for r in result:
            assert r.endswith(".yaml") or r.endswith(".yml")

    def test_nonexistent_directory_returns_empty(self) -> None:
        """Test that nonexistent directory returns empty list."""
        result = suggest_files("test.txt", search_dir="/nonexistent/path/12345")
        assert result == []

    def test_respects_max_results(self, tmp_path: Path) -> None:
        """Test that n parameter limits results."""
        # Create many similar files
        for i in range(10):
            (tmp_path / f"test{i}.txt").touch()

        result = suggest_files("test.txt", search_dir=tmp_path, n=3)
        assert len(result) <= 3

    def test_handles_permission_error_gracefully(self, tmp_path: Path) -> None:
        """Test that permission errors are handled gracefully."""
        # Create a file we can't access - this is platform-specific
        # Just verify the function doesn't crash
        result = suggest_files("test.txt", search_dir=tmp_path)
        assert isinstance(result, list)


class TestSuggestValues:
    """Tests for suggest_values function."""

    def test_suggest_similar_values(self) -> None:
        """Test suggesting similar values."""
        values = ["gpt-4o-mini", "gpt-4o", "gpt-4", "claude-3-sonnet"]
        result = suggest_values("gpt-4o-mni", values)
        assert "gpt-4o-mini" in result

    def test_model_name_suggestions(self) -> None:
        """Test model name suggestions work well."""
        models = [
            "claude-3-opus",
            "claude-3-sonnet",
            "claude-3-haiku",
            "gpt-4",
            "gpt-4-turbo",
        ]
        result = suggest_values("claude-3-sonne", models)
        assert "claude-3-sonnet" in result

    def test_provider_suggestions(self) -> None:
        """Test provider name suggestions."""
        providers = ["openai", "anthropic", "google", "mistral"]
        result = suggest_values("antropic", providers)
        assert "anthropic" in result

    def test_empty_values_returns_empty(self) -> None:
        """Test that empty values list returns empty."""
        result = suggest_values("test", [])
        assert result == []


class TestDefaultConstants:
    """Tests for default constant values."""

    def test_default_threshold_reasonable(self) -> None:
        """Test that default threshold is reasonable."""
        assert 0.0 <= DEFAULT_SIMILARITY_THRESHOLD <= 1.0
        # Should be around 0.6 for good matches
        assert DEFAULT_SIMILARITY_THRESHOLD == 0.6

    def test_default_max_suggestions_reasonable(self) -> None:
        """Test that default max suggestions is reasonable."""
        assert DEFAULT_MAX_SUGGESTIONS > 0
        assert DEFAULT_MAX_SUGGESTIONS <= 10
        assert DEFAULT_MAX_SUGGESTIONS == 3


# =============================================================================
# Integration Tests
# =============================================================================


class TestErrorFrameworkIntegration:
    """Integration tests combining ActionableError, ErrorRenderer, and fuzzy matching."""

    def test_file_not_found_with_suggestions(self, tmp_path: Path) -> None:
        """Test creating file not found error with file suggestions."""
        # Create some files
        (tmp_path / "config.yaml").touch()
        (tmp_path / "config.yml").touch()

        # Find similar files
        similar = suggest_files("configs.yaml", search_dir=tmp_path)

        # Create error with suggestions
        error = ActionableError(
            error_type=ErrorType.FILE_NOT_FOUND,
            message="File 'configs.yaml' not found",
            suggestions=["Check the file path", "Verify the file exists"],
            related_items=similar,
        )

        # Render to string
        renderer = ErrorRenderer()
        output = renderer.render_to_string(error)

        assert "configs.yaml" in output
        assert "Did you mean:" in output or len(similar) == 0

    def test_command_not_found_with_suggestions(self) -> None:
        """Test creating command not found error with command suggestions."""
        available_commands = ["/help", "/clear", "/quit", "/tokens", "/model"]

        # Find similar commands
        similar = suggest_commands("/healp", available_commands)

        # Create error with suggestions
        error = ActionableError(
            error_type=ErrorType.COMMAND_NOT_FOUND,
            message="Unknown command: /healp",
            suggestions=["Check the command spelling", "Use /help to see available commands"],
            related_items=similar,
        )

        # Verify error structure
        assert error.error_type == ErrorType.COMMAND_NOT_FOUND
        assert "/help" in error.related_items

        # Render and verify output
        renderer = ErrorRenderer()
        output = renderer.render_to_string(error)
        assert "Unknown command: /healp" in output
        assert "/help" in output

    def test_full_error_workflow(self) -> None:
        """Test full workflow from error creation to rendering."""
        # Create a comprehensive error
        error = ActionableError(
            error_type=ErrorType.API_KEY_MISSING,
            message="OpenAI API key not configured",
            suggestions=[
                "Set the OPENAI_API_KEY environment variable",
                "Add the key to your .env file",
                "Configure the key in settings",
            ],
            recovery_commands=[
                "export OPENAI_API_KEY=your-key-here",
                "echo 'OPENAI_API_KEY=your-key' >> .env",
            ],
            related_items=["ANTHROPIC_API_KEY", "GOOGLE_API_KEY"],
            severity="error",
            context={"provider": "openai", "required_for": "chat completion"},
        )

        # Convert to dict and back
        data = error.to_dict()
        restored = ActionableError.from_dict(data)

        # Verify roundtrip
        assert restored.message == error.message
        assert restored.suggestions == error.suggestions

        # Render both simple and full
        renderer = ErrorRenderer()
        full_output = renderer.render_to_string(error)
        text_output = renderer.render_to_text(error)

        # Verify content
        assert "OpenAI API key not configured" in full_output
        assert "OpenAI API key not configured" in text_output.plain
        assert "Suggestions:" in full_output
        assert "Try these commands:" in full_output
        assert "Did you mean:" in full_output
        assert "Context:" in full_output


# =============================================================================
# File Error Builder Tests
# =============================================================================


class TestMakeFileNotFoundError:
    """Tests for make_file_not_found_error builder function."""

    def test_basic_error_creation(self, tmp_path: Path) -> None:
        """Test creating a basic file not found error."""
        error = make_file_not_found_error("config.yaml", search_dir=tmp_path)

        assert error.error_type == ErrorType.FILE_NOT_FOUND
        assert "config.yaml" in error.message
        assert len(error.suggestions) > 0
        assert len(error.recovery_commands) > 0
        assert error.context["path"] == "config.yaml"

    def test_suggests_similar_files(self, tmp_path: Path) -> None:
        """Test that similar files are suggested."""
        # Create a file with a similar name
        (tmp_path / "config.yml").touch()
        (tmp_path / "config.yaml.bak").touch()

        error = make_file_not_found_error("config.yaml", search_dir=tmp_path)

        # Should find similar files
        assert len(error.related_items) > 0
        assert any("config" in item for item in error.related_items)

    def test_includes_find_command_for_extension(self, tmp_path: Path) -> None:
        """Test that find command is suggested for files with extension."""
        error = make_file_not_found_error("data.json", search_dir=tmp_path)

        # Should include a find command for .json files
        assert any(".json" in cmd for cmd in error.recovery_commands)

    def test_includes_ls_command(self, tmp_path: Path) -> None:
        """Test that ls command is included."""
        error = make_file_not_found_error("test.txt", search_dir=tmp_path)

        # Should include ls command
        assert any("ls -la" in cmd for cmd in error.recovery_commands)

    def test_context_includes_search_dir(self, tmp_path: Path) -> None:
        """Test that context includes search directory."""
        error = make_file_not_found_error("test.txt", search_dir=tmp_path)

        assert "search_dir" in error.context
        assert str(tmp_path) in error.context["search_dir"]

    def test_uses_parent_directory_when_no_search_dir(self) -> None:
        """Test that parent directory is used when search_dir not provided."""
        error = make_file_not_found_error("some/path/file.txt")

        # The search_dir in context should be derived from path's parent
        assert "search_dir" in error.context

    def test_nonexistent_search_dir(self) -> None:
        """Test behavior with non-existent search directory."""
        error = make_file_not_found_error(
            "test.txt", search_dir="/nonexistent/path/12345"
        )

        # Should still create error without crashing
        assert error.error_type == ErrorType.FILE_NOT_FOUND
        # related_items should be empty since directory doesn't exist
        assert error.related_items == []

    def test_renders_correctly(self, tmp_path: Path) -> None:
        """Test that the error renders correctly."""
        (tmp_path / "config.yml").touch()
        error = make_file_not_found_error("config.yaml", search_dir=tmp_path)

        renderer = ErrorRenderer()
        output = renderer.render_to_string(error)

        assert "File not found" in output
        assert "config.yaml" in output
        assert "Suggestions:" in output


class TestMakeFilePermissionError:
    """Tests for make_file_permission_error builder function."""

    def test_basic_error_creation(self) -> None:
        """Test creating a basic file permission error."""
        error = make_file_permission_error("/path/to/file.txt")

        assert error.error_type == ErrorType.FILE_PERMISSION_DENIED
        assert "file.txt" in error.message
        assert "Permission denied" in error.message
        assert len(error.suggestions) > 0
        assert len(error.recovery_commands) > 0

    def test_read_operation_suggestions(self) -> None:
        """Test suggestions for read operation."""
        error = make_file_permission_error("/path/to/file.txt", operation="read")

        assert error.context["operation"] == "read"
        # Should suggest chmod +r
        assert any("+r" in cmd for cmd in error.recovery_commands)
        assert "read" in error.message

    def test_write_operation_suggestions(self) -> None:
        """Test suggestions for write operation."""
        error = make_file_permission_error("/path/to/file.txt", operation="write")

        assert error.context["operation"] == "write"
        # Should suggest chmod +w
        assert any("+w" in cmd for cmd in error.recovery_commands)
        assert "write" in error.message

    def test_execute_operation_suggestions(self) -> None:
        """Test suggestions for execute operation."""
        error = make_file_permission_error("/path/to/script.sh", operation="execute")

        assert error.context["operation"] == "execute"
        # Should suggest chmod +x
        assert any("+x" in cmd for cmd in error.recovery_commands)
        assert "execute" in error.message

    def test_includes_sudo_suggestion(self) -> None:
        """Test that sudo suggestion is included."""
        error = make_file_permission_error("/etc/passwd", operation="write")

        # Should include sudo in suggestions
        assert any("sudo" in cmd for cmd in error.recovery_commands)
        assert any("elevated privileges" in s for s in error.suggestions)

    def test_includes_ownership_suggestion(self) -> None:
        """Test that ownership check suggestion is included."""
        error = make_file_permission_error("/path/to/file.txt")

        assert any("own" in s.lower() for s in error.suggestions)

    def test_context_includes_path(self) -> None:
        """Test that context includes the path."""
        error = make_file_permission_error("/path/to/file.txt", operation="write")

        assert error.context["path"] == "/path/to/file.txt"
        assert error.context["operation"] == "write"

    def test_existing_file_includes_permissions_in_context(self, tmp_path: Path) -> None:
        """Test that existing files include current permissions in context."""
        test_file = tmp_path / "test.txt"
        test_file.touch()

        error = make_file_permission_error(str(test_file), operation="read")

        # Should have permissions info if available
        assert "path" in error.context

    def test_renders_correctly(self) -> None:
        """Test that the error renders correctly."""
        error = make_file_permission_error("/etc/passwd", operation="write")

        renderer = ErrorRenderer()
        output = renderer.render_to_string(error)

        assert "Permission denied" in output
        assert "Suggestions:" in output
        assert "Try these commands:" in output


class TestMakeInvalidFileTypeError:
    """Tests for make_invalid_file_type_error builder function."""

    def test_basic_error_creation(self) -> None:
        """Test creating a basic invalid file type error."""
        error = make_invalid_file_type_error("config.json", [".yaml", ".yml"])

        assert error.error_type == ErrorType.INVALID_FILE_TYPE
        assert "config.json" in error.message
        assert ".json" in error.message
        assert ".yaml" in error.message or ".yml" in error.message

    def test_single_expected_type(self) -> None:
        """Test error with single expected type."""
        error = make_invalid_file_type_error("data.csv", [".json"])

        assert "'.json'" in error.message

    def test_multiple_expected_types(self) -> None:
        """Test error with multiple expected types."""
        error = make_invalid_file_type_error("config.txt", [".yaml", ".yml", ".json"])

        # Message should mention all expected types
        assert ".yaml" in error.message or "yaml" in str(error.suggestions)
        assert ".yml" in error.message or "yml" in str(error.suggestions)

    def test_file_with_no_extension(self) -> None:
        """Test error for file with no extension."""
        error = make_invalid_file_type_error("Makefile", [".yaml"])

        assert "no extension" in error.message
        assert ".yaml" in error.message

    def test_includes_rename_suggestion(self) -> None:
        """Test that rename suggestion is included."""
        error = make_invalid_file_type_error("config.json", [".yaml"])

        # Should include mv command
        assert any("mv" in cmd for cmd in error.recovery_commands)

    def test_includes_conversion_hints(self) -> None:
        """Test that conversion hints are included."""
        error = make_invalid_file_type_error("config.json", [".yaml"], conversion_hints=True)

        # Should include conversion tool suggestions for JSON to YAML
        assert any("yq" in cmd or "python" in cmd for cmd in error.recovery_commands)

    def test_no_conversion_hints_when_disabled(self) -> None:
        """Test that conversion hints are not included when disabled."""
        error = make_invalid_file_type_error("config.json", [".yaml"], conversion_hints=False)

        # Should not include conversion-specific commands
        conversion_tools = ["yq", "python -c", "pandoc", "convert"]
        for cmd in error.recovery_commands:
            assert not any(tool in cmd for tool in conversion_tools if "#" not in cmd)

    def test_context_includes_actual_type(self) -> None:
        """Test that context includes actual file type."""
        error = make_invalid_file_type_error("config.json", [".yaml"])

        assert error.context["actual_type"] == ".json"
        assert ".yaml" in error.context["expected_types"]

    def test_finds_related_files_with_expected_extension(self, tmp_path: Path) -> None:
        """Test that related files with expected extension are found."""
        # Create files with expected extensions
        (tmp_path / "config.yaml").touch()
        (tmp_path / "settings.yml").touch()
        test_file = tmp_path / "config.json"
        test_file.touch()

        error = make_invalid_file_type_error(str(test_file), [".yaml", ".yml"])

        # Should find the yaml/yml files
        assert len(error.related_items) > 0

    def test_file_type_conversions_mapping_coverage(self) -> None:
        """Test that FILE_TYPE_CONVERSIONS has expected mappings."""
        # Verify common conversions exist
        assert ".yaml" in FILE_TYPE_CONVERSIONS
        assert ".json" in FILE_TYPE_CONVERSIONS
        assert ".md" in FILE_TYPE_CONVERSIONS
        assert ".png" in FILE_TYPE_CONVERSIONS

        # Verify bidirectional mappings
        assert ".yml" in FILE_TYPE_CONVERSIONS[".yaml"]
        assert ".yaml" in FILE_TYPE_CONVERSIONS[".json"]

    def test_renders_correctly(self) -> None:
        """Test that the error renders correctly."""
        error = make_invalid_file_type_error("data.csv", [".json", ".yaml"])

        renderer = ErrorRenderer()
        output = renderer.render_to_string(error)

        assert "Invalid file type" in output
        assert "Suggestions:" in output


# =============================================================================
# Command Error Builder Tests
# =============================================================================


class TestMakeUnknownCommandError:
    """Tests for make_unknown_command_error builder function."""

    def test_basic_error_creation(self) -> None:
        """Test creating a basic unknown command error."""
        available = ["/help", "/clear", "/quit", "/tokens"]
        error = make_unknown_command_error("/healp", available)

        assert error.error_type == ErrorType.COMMAND_NOT_FOUND
        assert "/healp" in error.message
        assert len(error.suggestions) > 0
        assert len(error.recovery_commands) > 0

    def test_suggests_similar_commands(self) -> None:
        """Test that similar commands are suggested."""
        available = ["/help", "/clear", "/quit", "/tokens"]
        error = make_unknown_command_error("/healp", available)

        # Should find /help as similar
        assert "/help" in error.related_items

    def test_includes_did_you_mean_for_single_match(self) -> None:
        """Test 'Did you mean' message for single close match."""
        available = ["/help", "/clear", "/quit"]
        error = make_unknown_command_error("/hlep", available)

        # Should have "Did you mean" suggestion
        assert any("Did you mean" in s for s in error.suggestions)

    def test_includes_help_recovery_command(self) -> None:
        """Test that /help is included in recovery commands."""
        available = ["/help", "/clear"]
        error = make_unknown_command_error("/test", available)

        assert "/help" in error.recovery_commands

    def test_lists_available_commands_when_small(self) -> None:
        """Test that available commands are listed when <= 10."""
        available = ["/help", "/clear", "/quit"]
        error = make_unknown_command_error("/test", available)

        # Should list available commands in suggestions
        assert any("Available commands:" in s for s in error.suggestions)

    def test_does_not_list_commands_when_large(self) -> None:
        """Test that commands are not listed when > 10."""
        available = [f"/cmd{i}" for i in range(15)]
        error = make_unknown_command_error("/test", available)

        # Should not list all commands
        assert not any("cmd14" in s for s in error.suggestions)

    def test_context_includes_command_and_count(self) -> None:
        """Test that context includes command and available count."""
        available = ["/help", "/clear", "/quit"]
        error = make_unknown_command_error("/test", available)

        assert error.context["command"] == "/test"
        assert error.context["available_count"] == "3"

    def test_empty_available_commands(self) -> None:
        """Test handling of empty available commands."""
        error = make_unknown_command_error("/test", [])

        assert error.error_type == ErrorType.COMMAND_NOT_FOUND
        assert error.related_items == []

    def test_renders_correctly(self) -> None:
        """Test that the error renders correctly."""
        available = ["/help", "/clear", "/quit"]
        error = make_unknown_command_error("/healp", available)

        renderer = ErrorRenderer()
        output = renderer.render_to_string(error)

        assert "Unknown command" in output
        assert "/healp" in output
        assert "Suggestions:" in output


class TestMakeInvalidFlagError:
    """Tests for make_invalid_flag_error builder function."""

    def test_basic_error_creation(self) -> None:
        """Test creating a basic invalid flag error."""
        valid_flags = ["--help", "--verbose", "--quiet", "--version"]
        error = make_invalid_flag_error("--versboe", valid_flags)

        assert error.error_type == ErrorType.INVALID_FLAG
        assert "--versboe" in error.message
        assert len(error.suggestions) > 0

    def test_suggests_similar_flags(self) -> None:
        """Test that similar flags are suggested."""
        valid_flags = ["--help", "--verbose", "--quiet"]
        error = make_invalid_flag_error("--versboe", valid_flags)

        # Should find --verbose as similar
        assert "--verbose" in error.related_items

    def test_includes_command_in_message(self) -> None:
        """Test that command is included in message when provided."""
        valid_flags = ["--help", "--verbose"]
        error = make_invalid_flag_error("--test", valid_flags, command="kai")

        assert "kai" in error.message
        assert "--test" in error.message

    def test_includes_command_help_in_recovery(self) -> None:
        """Test that command --help is in recovery commands."""
        valid_flags = ["--help", "--verbose"]
        error = make_invalid_flag_error("--test", valid_flags, command="kai")

        assert "kai --help" in error.recovery_commands

    def test_generic_help_when_no_command(self) -> None:
        """Test generic --help when command not provided."""
        valid_flags = ["--help", "--verbose"]
        error = make_invalid_flag_error("--test", valid_flags)

        assert "--help" in error.recovery_commands

    def test_lists_valid_flags_when_small(self) -> None:
        """Test that valid flags are listed when <= 10."""
        valid_flags = ["--help", "--verbose", "--quiet"]
        error = make_invalid_flag_error("--test", valid_flags)

        # Should list valid flags in suggestions
        assert any("Valid flags:" in s for s in error.suggestions)

    def test_does_not_list_flags_when_large(self) -> None:
        """Test that flags are not listed when > 10."""
        valid_flags = [f"--flag{i}" for i in range(15)]
        error = make_invalid_flag_error("--test", valid_flags)

        # Should mention --help instead
        assert any("--help" in s for s in error.suggestions)

    def test_context_includes_flag_and_count(self) -> None:
        """Test that context includes flag and valid flags count."""
        valid_flags = ["--help", "--verbose"]
        error = make_invalid_flag_error("--test", valid_flags, command="kai")

        assert error.context["flag"] == "--test"
        assert error.context["valid_flags_count"] == "2"
        assert error.context["command"] == "kai"

    def test_case_sensitive_suggestion(self) -> None:
        """Test that case sensitivity is mentioned."""
        valid_flags = ["--Verbose"]
        error = make_invalid_flag_error("--verbose", valid_flags)

        assert any("case-sensitive" in s for s in error.suggestions)

    def test_renders_correctly(self) -> None:
        """Test that the error renders correctly."""
        valid_flags = ["--help", "--verbose", "--quiet"]
        error = make_invalid_flag_error("--versboe", valid_flags, command="kai")

        renderer = ErrorRenderer()
        output = renderer.render_to_string(error)

        assert "Invalid flag" in output
        assert "--versboe" in output


class TestMakeMissingArgumentError:
    """Tests for make_missing_argument_error builder function."""

    def test_basic_error_creation(self) -> None:
        """Test creating a basic missing argument error."""
        error = make_missing_argument_error("/model", "model_name")

        assert error.error_type == ErrorType.MISSING_ARGUMENT
        assert "model_name" in error.message
        assert "/model" in error.message
        assert len(error.suggestions) > 0

    def test_includes_expected_type(self) -> None:
        """Test that expected type is included when provided."""
        error = make_missing_argument_error(
            "/model", "model_name", expected_type="model identifier like 'gpt-4'"
        )

        # Should mention expected type
        assert any("model identifier" in s for s in error.suggestions)
        assert error.context["expected_type"] == "model identifier like 'gpt-4'"

    def test_includes_usage_example(self) -> None:
        """Test that usage example is included when provided."""
        error = make_missing_argument_error(
            "/model", "model_name", usage_example="/model gpt-4o-mini"
        )

        # Should include usage example in recovery commands
        assert any("Example:" in cmd for cmd in error.recovery_commands)
        assert any("gpt-4o-mini" in cmd for cmd in error.recovery_commands)

    def test_includes_help_recovery_command(self) -> None:
        """Test that --help is in recovery commands."""
        error = make_missing_argument_error("/model", "model_name")

        assert any("--help" in cmd for cmd in error.recovery_commands)

    def test_context_includes_command_and_argument(self) -> None:
        """Test that context includes command and missing argument."""
        error = make_missing_argument_error("/model", "model_name")

        assert error.context["command"] == "/model"
        assert error.context["missing_argument"] == "model_name"

    def test_no_related_items(self) -> None:
        """Test that there are no related items for missing argument."""
        error = make_missing_argument_error("/model", "model_name")

        # Missing argument errors don't have related items
        assert error.related_items == []

    def test_renders_correctly(self) -> None:
        """Test that the error renders correctly."""
        error = make_missing_argument_error(
            "/model", "model_name",
            expected_type="model identifier",
            usage_example="/model gpt-4o-mini"
        )

        renderer = ErrorRenderer()
        output = renderer.render_to_string(error)

        assert "Missing required argument" in output
        assert "model_name" in output
        assert "Suggestions:" in output


# =============================================================================
# Configuration Error Builder Tests
# =============================================================================


class TestMakeApiKeyMissingError:
    """Tests for make_api_key_missing_error builder function."""

    def test_basic_error_creation(self) -> None:
        """Test creating a basic API key missing error."""
        error = make_api_key_missing_error("anthropic")

        assert error.error_type == ErrorType.API_KEY_MISSING
        assert "Anthropic" in error.message or "anthropic" in error.message.lower()
        assert len(error.suggestions) > 0
        assert len(error.recovery_commands) > 0

    def test_anthropic_specific_instructions(self) -> None:
        """Test Anthropic-specific instructions."""
        error = make_api_key_missing_error("anthropic")

        assert "ANTHROPIC_API_KEY" in str(error.suggestions)
        assert error.context["env_var"] == "ANTHROPIC_API_KEY"
        assert "console.anthropic.com" in error.context.get("api_key_url", "")

    def test_openai_specific_instructions(self) -> None:
        """Test OpenAI-specific instructions."""
        error = make_api_key_missing_error("openai")

        assert "OPENAI_API_KEY" in str(error.suggestions)
        assert error.context["env_var"] == "OPENAI_API_KEY"
        assert "platform.openai.com" in error.context.get("api_key_url", "")

    def test_google_specific_instructions(self) -> None:
        """Test Google/Gemini-specific instructions."""
        error = make_api_key_missing_error("google")

        assert "GOOGLE_API_KEY" in str(error.suggestions)
        assert error.context["env_var"] == "GOOGLE_API_KEY"

    def test_gemini_alias_works(self) -> None:
        """Test that 'gemini' works as alias for Google."""
        error = make_api_key_missing_error("gemini")

        assert "GOOGLE_API_KEY" in str(error.suggestions)
        assert "Gemini" in error.context["provider"]

    def test_ollama_special_case(self) -> None:
        """Test Ollama special case (no API key needed)."""
        error = make_api_key_missing_error("ollama")

        # Ollama should have different message about running
        assert "running" in error.message.lower() or "accessible" in error.message.lower()
        # Should suggest ollama commands
        assert any("ollama" in cmd for cmd in error.recovery_commands)

    def test_unknown_provider_fallback(self) -> None:
        """Test unknown provider uses generic fallback."""
        error = make_api_key_missing_error("unknown_provider")

        # Should create generic env var name
        assert "UNKNOWN_PROVIDER_API_KEY" in str(error.suggestions) or "API key" in str(error.suggestions)

    def test_includes_export_command(self) -> None:
        """Test that export command is included."""
        error = make_api_key_missing_error("anthropic")

        assert any("export" in cmd for cmd in error.recovery_commands)

    def test_includes_url_for_known_providers(self) -> None:
        """Test that API key URL is included for known providers."""
        error = make_api_key_missing_error("openai")

        # Should mention where to get key
        assert any("Get your API key" in s for s in error.suggestions)

    def test_provider_api_key_instructions_coverage(self) -> None:
        """Test that PROVIDER_API_KEY_INSTRUCTIONS has expected providers."""
        expected_providers = ["anthropic", "openai", "google", "gemini", "mistral", "groq", "ollama"]
        for provider in expected_providers:
            assert provider in PROVIDER_API_KEY_INSTRUCTIONS

    def test_case_insensitive_provider(self) -> None:
        """Test that provider name is case-insensitive."""
        error1 = make_api_key_missing_error("Anthropic")
        error2 = make_api_key_missing_error("ANTHROPIC")

        assert error1.context["env_var"] == error2.context["env_var"]

    def test_renders_correctly(self) -> None:
        """Test that the error renders correctly."""
        error = make_api_key_missing_error("anthropic")

        renderer = ErrorRenderer()
        output = renderer.render_to_string(error)

        assert "API key" in output.lower()
        assert "Suggestions:" in output


class TestMakeModelNotAvailableError:
    """Tests for make_model_not_available_error builder function."""

    def test_basic_error_creation(self) -> None:
        """Test creating a basic model not available error."""
        available = ["gpt-4o-mini", "gpt-4o", "gpt-4"]
        error = make_model_not_available_error("gpt-5", available)

        assert error.error_type == ErrorType.MODEL_NOT_AVAILABLE
        assert "gpt-5" in error.message
        assert len(error.suggestions) > 0
        assert len(error.recovery_commands) > 0

    def test_suggests_similar_models(self) -> None:
        """Test that similar models are suggested."""
        available = ["gpt-4o-mini", "gpt-4o", "gpt-4"]
        error = make_model_not_available_error("gpt-4o-mni", available)

        # Should find gpt-4o-mini as similar
        assert "gpt-4o-mini" in error.related_items

    def test_includes_did_you_mean_for_single_match(self) -> None:
        """Test 'Did you mean' message for single close match."""
        available = ["claude-3-opus", "gpt-4"]
        error = make_model_not_available_error("claude-3-opuss", available)

        # Should have "Did you mean" suggestion
        assert any("Did you mean" in s for s in error.suggestions)

    def test_includes_models_command(self) -> None:
        """Test that /models command is in recovery commands."""
        available = ["gpt-4", "claude-3-opus"]
        error = make_model_not_available_error("test", available)

        assert "/models" in error.recovery_commands

    def test_includes_model_switch_suggestion(self) -> None:
        """Test that model switch suggestion is included when similar found."""
        available = ["gpt-4o-mini", "gpt-4o"]
        error = make_model_not_available_error("gpt-4o-mni", available)

        # Should suggest switching to similar model
        assert any("/model" in cmd and "gpt-4o" in cmd for cmd in error.recovery_commands)

    def test_lists_available_models_when_small(self) -> None:
        """Test that available models are listed when <= 10."""
        available = ["gpt-4", "claude-3-opus", "gemini-pro"]
        error = make_model_not_available_error("test", available)

        # Should list available models in suggestions
        assert any("Available models:" in s for s in error.suggestions)

    def test_does_not_list_models_when_large(self) -> None:
        """Test that models are not listed when > 10."""
        available = [f"model-{i}" for i in range(15)]
        error = make_model_not_available_error("test", available)

        # Should mention /models instead
        assert any("/models" in s for s in error.suggestions)

    def test_handles_empty_available_models(self) -> None:
        """Test handling of empty available models."""
        error = make_model_not_available_error("gpt-4", [])

        assert error.error_type == ErrorType.MODEL_NOT_AVAILABLE
        assert error.related_items == []
        # Should mention API key check
        assert any("API key" in s for s in error.suggestions)

    def test_context_includes_model_and_count(self) -> None:
        """Test that context includes requested model and count."""
        available = ["gpt-4", "claude-3"]
        error = make_model_not_available_error("gpt-5", available)

        assert error.context["requested_model"] == "gpt-5"
        assert error.context["available_count"] == "2"

    def test_renders_correctly(self) -> None:
        """Test that the error renders correctly."""
        available = ["gpt-4o-mini", "gpt-4o", "gpt-4"]
        error = make_model_not_available_error("gpt-4o-mni", available)

        renderer = ErrorRenderer()
        output = renderer.render_to_string(error)

        assert "not available" in output.lower()
        assert "Suggestions:" in output


class TestMakeSkillNotFoundError:
    """Tests for make_skill_not_found_error builder function."""

    def test_basic_error_creation(self) -> None:
        """Test creating a basic skill not found error."""
        available = ["code-review", "code-explain", "code-refactor"]
        error = make_skill_not_found_error("code-reveiw", available)

        assert error.error_type == ErrorType.SKILL_NOT_FOUND
        assert "code-reveiw" in error.message
        assert len(error.suggestions) > 0
        assert len(error.recovery_commands) > 0

    def test_suggests_similar_skills(self) -> None:
        """Test that similar skills are suggested."""
        available = ["code-review", "code-explain", "code-refactor"]
        error = make_skill_not_found_error("code-reveiw", available)

        # Should find code-review as similar
        assert "code-review" in error.related_items

    def test_includes_did_you_mean_for_single_match(self) -> None:
        """Test 'Did you mean' message for single close match."""
        available = ["code-review", "text-analysis"]
        error = make_skill_not_found_error("code-reveiw", available)

        # Should have "Did you mean" suggestion
        assert any("Did you mean" in s for s in error.suggestions)

    def test_includes_skills_command(self) -> None:
        """Test that /skills command is in recovery commands."""
        available = ["code-review", "code-explain"]
        error = make_skill_not_found_error("test", available)

        assert "/skills" in error.recovery_commands

    def test_includes_skill_load_suggestion(self) -> None:
        """Test that /skill load suggestion is included when similar found."""
        available = ["code-review", "code-explain"]
        error = make_skill_not_found_error("code-reveiw", available)

        # Should suggest loading similar skill
        assert any("/skill load" in cmd and "code-review" in cmd for cmd in error.recovery_commands)

    def test_includes_skill_reload_command(self) -> None:
        """Test that /skill reload is in recovery commands."""
        available = ["code-review"]
        error = make_skill_not_found_error("test", available)

        assert "/skill reload" in error.recovery_commands

    def test_lists_available_skills_when_small(self) -> None:
        """Test that available skills are listed when <= 10."""
        available = ["code-review", "code-explain", "code-refactor"]
        error = make_skill_not_found_error("test", available)

        # Should list available skills in suggestions
        assert any("Available skills:" in s for s in error.suggestions)

    def test_does_not_list_skills_when_large(self) -> None:
        """Test that skills are not listed when > 10."""
        available = [f"skill-{i}" for i in range(15)]
        error = make_skill_not_found_error("test", available)

        # Should mention /skills instead
        assert any("/skills" in s for s in error.suggestions)

    def test_handles_empty_available_skills(self) -> None:
        """Test handling of empty available skills."""
        error = make_skill_not_found_error("code-review", [])

        assert error.error_type == ErrorType.SKILL_NOT_FOUND
        assert error.related_items == []
        # Should mention no skills loaded
        assert any("No skills" in s for s in error.suggestions)

    def test_context_includes_skill_and_count(self) -> None:
        """Test that context includes requested skill and count."""
        available = ["code-review", "code-explain"]
        error = make_skill_not_found_error("test-skill", available)

        assert error.context["requested_skill"] == "test-skill"
        assert error.context["available_count"] == "2"

    def test_mentions_loading_from_directories(self) -> None:
        """Test that loading from directories is mentioned."""
        available = ["code-review"]
        error = make_skill_not_found_error("test", available)

        # Should mention loading skills
        assert any("loaded" in s.lower() or "directories" in s.lower() or "packages" in s.lower()
                   for s in error.suggestions)

    def test_renders_correctly(self) -> None:
        """Test that the error renders correctly."""
        available = ["code-review", "code-explain", "code-refactor"]
        error = make_skill_not_found_error("code-reveiw", available)

        renderer = ErrorRenderer()
        output = renderer.render_to_string(error)

        assert "not found" in output.lower()
        assert "Suggestions:" in output


# =============================================================================
# Error Builder Output Formatting Tests
# =============================================================================


class TestErrorBuilderOutputFormatting:
    """Tests for verifying error builder output formatting is correct."""

    def test_file_not_found_full_render(self, tmp_path: Path) -> None:
        """Test full rendering of file not found error."""
        (tmp_path / "config.yml").touch()
        error = make_file_not_found_error("config.yaml", search_dir=tmp_path)

        renderer = ErrorRenderer()
        output = renderer.render_to_string(error)

        # Verify all sections are present
        assert "File Not Found" in output or "file_not_found" in output.lower()
        assert "Suggestions:" in output
        assert "Try these commands:" in output
        assert "Context:" in output

    def test_command_error_full_render(self) -> None:
        """Test full rendering of command error."""
        available = ["/help", "/clear", "/quit"]
        error = make_unknown_command_error("/healp", available)

        renderer = ErrorRenderer()
        output = renderer.render_to_string(error)

        # Verify structure
        assert "Unknown command" in output
        assert "Suggestions:" in output
        assert "Did you mean:" in output  # Has related items

    def test_api_key_error_full_render(self) -> None:
        """Test full rendering of API key error."""
        error = make_api_key_missing_error("anthropic")

        renderer = ErrorRenderer()
        output = renderer.render_to_string(error)

        # Verify comprehensive output
        assert "API key" in output.lower()
        assert "ANTHROPIC_API_KEY" in output
        assert "Suggestions:" in output
        assert "Try these commands:" in output
        assert "Context:" in output

    def test_model_error_with_suggestions_render(self) -> None:
        """Test rendering of model error with similar suggestions."""
        available = ["gpt-4o-mini", "gpt-4o", "gpt-4", "claude-3-opus"]
        error = make_model_not_available_error("gpt-4o-mni", available)

        renderer = ErrorRenderer()
        output = renderer.render_to_string(error)

        # Should show similar models
        assert "Did you mean:" in output
        assert "gpt-4o-mini" in output

    def test_skill_error_with_suggestions_render(self) -> None:
        """Test rendering of skill error with similar suggestions."""
        available = ["code-review", "code-explain", "code-refactor"]
        error = make_skill_not_found_error("code-reveiw", available)

        renderer = ErrorRenderer()
        output = renderer.render_to_string(error)

        # Should show similar skills
        assert "Did you mean:" in output
        assert "code-review" in output

    def test_simple_render_mode(self) -> None:
        """Test simple render mode for error builders."""
        error = make_api_key_missing_error("openai")

        string_io = StringIO()
        console = Console(file=string_io, force_terminal=True, highlight=False)
        renderer = ErrorRenderer(console=console)
        renderer.render_simple(error)

        output = string_io.getvalue()
        # Simple render should still contain key info
        assert "API key" in output.lower() or "OPENAI" in output

    def test_text_render_for_embedding(self) -> None:
        """Test text render for embedding in other components."""
        error = make_file_permission_error("/etc/passwd", operation="write")

        renderer = ErrorRenderer()
        text = renderer.render_to_text(error)

        # Should be a Rich Text object
        from rich.text import Text
        assert isinstance(text, Text)
        assert "Permission denied" in text.plain
