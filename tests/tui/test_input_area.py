"""Tests for input area widget."""

import pytest
from kai_code.tui.widgets.input_area import InputArea


def test_input_area_empty():
    """Input area starts empty."""
    area = InputArea()
    assert area.value == ""


def test_input_area_placeholder():
    """Input area shows placeholder."""
    area = InputArea()
    assert area.placeholder != ""


def test_input_area_detects_slash_command():
    """Input area detects slash commands."""
    area = InputArea()
    assert area.is_slash_command("/help") is True
    assert area.is_slash_command("hello") is False
    assert area.is_slash_command("/model gpt-4") is True


def test_input_area_parse_slash_command():
    """Input area parses slash commands."""
    area = InputArea()
    cmd, args = area.parse_slash_command("/model gpt-4o")
    assert cmd == "model"
    assert args == "gpt-4o"


def test_input_area_parse_slash_command_no_args():
    """Input area parses slash commands without args."""
    area = InputArea()
    cmd, args = area.parse_slash_command("/help")
    assert cmd == "help"
    assert args == ""
