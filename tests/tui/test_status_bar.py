"""Tests for status bar widget."""

import pytest
from kai_code.tui.widgets.status_bar import StatusBar


def test_status_bar_default_content():
    """Status bar shows app name and default values."""
    bar = StatusBar()
    assert "kai-code" in bar.render_content()


def test_status_bar_model_display():
    """Status bar displays model name."""
    bar = StatusBar(model="gemini-2.0-flash")
    content = bar.render_content()
    assert "gemini-2.0-flash" in content


def test_status_bar_yolo_badge():
    """Status bar shows YOLO badge when enabled."""
    bar = StatusBar(yolo=True)
    content = bar.render_content()
    assert "YOLO" in content


def test_status_bar_session_name():
    """Status bar displays session name."""
    bar = StatusBar(session="myproject")
    content = bar.render_content()
    assert "myproject" in content
