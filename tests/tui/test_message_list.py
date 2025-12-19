"""Tests for message list widget."""

import pytest
from kai_code.tui.widgets.message_list import MessageList
from kai_code.tui.components.message import MessageRole


def test_message_list_empty():
    """Empty message list has no messages."""
    ml = MessageList()
    assert ml.message_count == 0


def test_message_list_add_message():
    """Can add messages to list."""
    ml = MessageList()
    ml.add_message(MessageRole.USER, "Hello")
    assert ml.message_count == 1


def test_message_list_multiple_messages():
    """Can add multiple messages."""
    ml = MessageList()
    ml.add_message(MessageRole.USER, "Hello")
    ml.add_message(MessageRole.ASSISTANT, "Hi there!")
    ml.add_message(MessageRole.TOOL, "Done", tool_name="execute")
    assert ml.message_count == 3


def test_message_list_clear():
    """Can clear all messages."""
    ml = MessageList()
    ml.add_message(MessageRole.USER, "Hello")
    ml.add_message(MessageRole.ASSISTANT, "Hi")
    ml.clear_messages()
    assert ml.message_count == 0


def test_message_list_get_streaming_message():
    """Can get current streaming message."""
    ml = MessageList()
    ml.add_message(MessageRole.USER, "Hello")
    msg = ml.add_streaming_message(MessageRole.ASSISTANT)
    assert ml.get_streaming_message() == msg
    assert msg.streaming is True
