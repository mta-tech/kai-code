"""Tests for slash commands."""

import pytest
from kai_code.tui.commands import CommandRegistry, COMMANDS


def test_commands_registry_has_help():
    """Registry includes /help command."""
    assert "help" in COMMANDS


def test_commands_registry_has_exit():
    """Registry includes /exit command."""
    assert "exit" in COMMANDS


def test_commands_registry_has_model():
    """Registry includes /model command."""
    assert "model" in COMMANDS


def test_commands_registry_has_yolo():
    """Registry includes /yolo command."""
    assert "yolo" in COMMANDS


def test_commands_registry_has_clear():
    """Registry includes /clear command."""
    assert "clear" in COMMANDS


def test_commands_get_help_text():
    """Can get help text for all commands."""
    registry = CommandRegistry()
    help_text = registry.get_help_text()
    assert "/help" in help_text
    assert "/exit" in help_text
    assert "/model" in help_text


def test_commands_is_valid():
    """Can check if command is valid."""
    registry = CommandRegistry()
    assert registry.is_valid("help") is True
    assert registry.is_valid("exit") is True
    assert registry.is_valid("nonexistent") is False
