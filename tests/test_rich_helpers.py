"""Test rich helper functions."""
import pytest
from kai_code.rich_helpers import (
    print_section_header,
    print_status,
    print_error,
    format_progress,
    print_step,
)
from unittest.mock import patch


def test_print_section_header(capsys):
    """Test section header prints with correct format."""
    print_section_header("Test Section")
    captured = capsys.readouterr()
    # Check for border characters (may be trimmed for terminal width)
    assert "═" in captured.out
    assert "Test Section" in captured.out
    # Ensure we have at least 2 border lines
    assert captured.out.count("═") >= 120


def test_print_status_success(capsys):
    """Test success status prints with checkmark."""
    print_status("success", "Operation completed")
    captured = capsys.readouterr()
    assert "[green]" in captured.out or "✓" in captured.out
    assert "Operation completed" in captured.out


def test_print_status_error(capsys):
    """Test error status prints with X mark."""
    print_status("error", "Operation failed")
    captured = capsys.readouterr()
    assert "[red]" in captured.out or "✗" in captured.out
    assert "Operation failed" in captured.out


def test_print_error_with_suggestion(capsys):
    """Test error prints with suggestion."""
    print_error("Connection failed", "Check network")
    captured = capsys.readouterr()
    assert "Connection failed" in captured.out
    assert "Check network" in captured.out


def test_format_progress():
    """Test progress formatting."""
    result = format_progress(3, 4)
    assert "75%" in result or "3/4" in result


def test_print_step(capsys):
    """Test step printing with indentation."""
    print_step(1, "Creating agent", "Agent ID: abc123")
    captured = capsys.readouterr()
    assert "1." in captured.out or "1)" in captured.out
    assert "Creating agent" in captured.out
    assert "Agent ID: abc123" in captured.out
