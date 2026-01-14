"""Test fixture: tools module for testing tool loader."""

from langchain_core.tools import tool


@tool("test_tool_one")
def test_tool_one(input: str) -> str:
    """A test tool that does something."""
    return f"Processed: {input}"


@tool("test_tool_two")
def test_tool_two(x: int, y: int) -> int:
    """Another test tool."""
    return x + y


def create_test_tools() -> list:
    """Create test tools (no parameters required)."""
    return [
        test_tool_one,
        test_tool_two,
    ]
