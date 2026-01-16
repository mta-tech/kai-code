"""Test rich helper functions."""

from kai_code.rich_helpers import (
    format_progress,
    print_error,
    print_section_header,
    print_status,
    print_step,
    print_summary,
)


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


def test_format_progress_edge_cases():
    """Test progress formatting with edge cases."""
    # Negative current value (normalized to 0)
    assert format_progress(-1, 10) == "0% (0/10)"

    # Zero total
    assert format_progress(5, 0) == "0% (0/0)"

    # Current > total (should cap at 100%)
    assert format_progress(15, 10) == "100% (15/10)"

    # Normal case
    assert format_progress(3, 4) == "75% (3/4)"


def test_print_summary(capsys):
    """Test summary printing with test results."""
    results = {
        "test_login": True,
        "test_logout": True,
        "test_connection": False,
    }
    print_summary(results)
    captured = capsys.readouterr()

    # Check that all test names appear
    assert "test_login" in captured.out
    assert "test_logout" in captured.out
    assert "test_connection" in captured.out

    # Check for summary section
    assert "Summary" in captured.out

    # Check for result summary
    assert "2/3" in captured.out

