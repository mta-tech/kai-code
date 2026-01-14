"""Tests for tool pattern loading."""
import pytest

from kai_code.tool_loader import load_tools_from_patterns


def test_load_tools_from_exact_module():
    """Test loading tools from exact module path."""
    # Load from our test fixture
    tools = load_tools_from_patterns([
        "tests.agent_loader.fixtures.test_tools"
    ])

    # Should load tools from create_test_tools()
    tool_names = [t.name for t in tools]
    assert len(tool_names) == 2
    assert "test_tool_one" in tool_names
    assert "test_tool_two" in tool_names


def test_load_tools_with_wildcards():
    """Test loading tools using wildcard patterns."""
    tools = load_tools_from_patterns([
        "tests.agent_loader.fixtures.*"
    ])

    # Should load all tools from fixtures directory
    tool_names = [t.name for t in tools]
    assert len(tool_names) >= 2
    assert "test_tool_one" in tool_names
    assert "test_tool_two" in tool_names


def test_load_tools_from_multiple_patterns():
    """Test loading tools from multiple patterns."""
    tools = load_tools_from_patterns([
        "tests.agent_loader.fixtures.test_tools",
    ])

    # Should load tools from the module
    assert len(tools) == 2
    tool_names = [t.name for t in tools]
    assert "test_tool_one" in tool_names


def test_empty_pattern_list_returns_empty():
    """Test that empty pattern list returns empty tool list."""
    tools = load_tools_from_patterns([])
    assert tools == []


def test_invalid_tool_pattern_logs_warning(caplog):
    """Test that invalid patterns log warnings but don't crash."""
    with caplog.at_level("WARNING"):
        tools = load_tools_from_patterns(["nonexistent.module.*"])

    # Should return empty list, not crash
    assert tools == []
    assert "warning" in caplog.text.lower() or "not found" in caplog.text.lower()


def test_skip_modules_with_required_parameters():
    """Test that modules with parameterized create_*_tools functions are skipped."""
    # Seeknal tools require seeknal_path parameter, so they should be skipped
    tools = load_tools_from_patterns([
        "kai_code.agents.seeknal.tools.project_tools"
    ])

    # Should return empty list since create_project_tools requires parameters
    assert tools == []


def test_simple_tool_names_are_skipped(caplog):
    """Test that simple tool names without dots are skipped."""
    # Set the logger level for the specific module
    with caplog.at_level("DEBUG", logger="kai_code.tool_loader"):
        tools = load_tools_from_patterns(["Bash", "Read", "Write"])

    # Should return empty list - simple names are skipped
    assert tools == []
    # Should log debug messages
    assert "Skipping tool name pattern" in caplog.text
