"""Tests for tool panel widget."""

import pytest
from kai_code.tui.widgets.tool_panel import ToolPanel, ToolStatus


def test_tool_panel_idle():
    """Tool panel shows idle state by default."""
    panel = ToolPanel()
    assert panel.status == ToolStatus.IDLE


def test_tool_panel_running():
    """Tool panel shows running tool."""
    panel = ToolPanel()
    panel.show_tool_running("execute", {"command": "pytest"})
    assert panel.status == ToolStatus.RUNNING
    assert panel.tool_name == "execute"


def test_tool_panel_complete():
    """Tool panel shows completed tool."""
    panel = ToolPanel()
    panel.show_tool_running("execute", {"command": "pytest"})
    panel.show_tool_result("All tests passed", exit_code=0)
    assert panel.status == ToolStatus.COMPLETE
    assert panel.exit_code == 0


def test_tool_panel_error():
    """Tool panel shows error state."""
    panel = ToolPanel()
    panel.show_tool_running("execute", {"command": "pytest"})
    panel.show_tool_result("Test failed", exit_code=1)
    assert panel.status == ToolStatus.ERROR
    assert panel.exit_code == 1


def test_tool_panel_reset():
    """Tool panel can be reset to idle."""
    panel = ToolPanel()
    panel.show_tool_running("execute", {"command": "pytest"})
    panel.reset()
    assert panel.status == ToolStatus.IDLE
