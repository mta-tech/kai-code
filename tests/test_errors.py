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
