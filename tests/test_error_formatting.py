"""Test error message formatting."""
import pytest
from unittest.mock import patch, MagicMock
from kai_code.rich_helpers import print_error


def test_print_error_basic(capsys):
    """Test basic error printing."""
    print_error("Test error")
    captured = capsys.readouterr()
    assert "Test error" in captured.out
    assert "✗" in captured.out


def test_print_error_with_suggestion(capsys):
    """Test error with suggestion."""
    print_error("Connection failed", "Check your network")
    captured = capsys.readouterr()
    assert "Connection failed" in captured.out
    assert "Check your network" in captured.out
    assert "Suggestion:" in captured.out or "└─" in captured.out


@pytest.mark.asyncio
async def test_agent_error_formatting():
    """Test agent errors include suggestions."""
    # This would be an integration test
    # Verify that actual agent errors follow the format
    pass
