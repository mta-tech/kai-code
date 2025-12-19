"""Tests for approval modal widget."""

import pytest
from kai_code.tui.widgets.approval_modal import ApprovalModal, ApprovalDecision


def test_approval_modal_creates():
    """Can create approval modal."""
    modal = ApprovalModal(
        tool_name="execute",
        tool_args={"command": "rm -rf /tmp/test"},
    )
    assert modal.tool_name == "execute"


def test_approval_modal_shows_tool_name():
    """Modal displays tool name."""
    modal = ApprovalModal(
        tool_name="execute",
        tool_args={"command": "pytest"},
    )
    content = modal.render_content()
    assert "execute" in content


def test_approval_modal_shows_args():
    """Modal displays tool arguments."""
    modal = ApprovalModal(
        tool_name="execute",
        tool_args={"command": "pytest tests/"},
    )
    content = modal.render_content()
    assert "pytest tests/" in content


def test_approval_decision_enum():
    """ApprovalDecision has expected values."""
    assert ApprovalDecision.APPROVE.value == "approve"
    assert ApprovalDecision.REJECT.value == "reject"
    assert ApprovalDecision.EDIT.value == "edit"
