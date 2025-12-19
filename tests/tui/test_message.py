"""Tests for message component."""

import pytest
from kai_code.tui.components.message import Message, MessageRole


def test_user_message_content():
    """User message displays content."""
    msg = Message(role=MessageRole.USER, content="Hello world")
    assert msg.content == "Hello world"
    assert msg.role == MessageRole.USER


def test_assistant_message_content():
    """Assistant message displays content."""
    msg = Message(role=MessageRole.ASSISTANT, content="Hi there!")
    assert msg.content == "Hi there!"
    assert msg.role == MessageRole.ASSISTANT


def test_tool_message_content():
    """Tool message displays tool name and result."""
    msg = Message(
        role=MessageRole.TOOL,
        content="Exit code: 0",
        tool_name="execute",
    )
    assert msg.tool_name == "execute"
    assert "Exit code: 0" in msg.content


def test_message_streaming_state():
    """Message tracks streaming state."""
    msg = Message(role=MessageRole.ASSISTANT, content="", streaming=True)
    assert msg.streaming is True
    msg.append_content("Hello")
    assert msg.content == "Hello"
    msg.finish_streaming()
    assert msg.streaming is False
