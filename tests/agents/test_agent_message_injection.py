"""Tests for _add_system_message method on KaiAgent."""

import pytest
from pathlib import Path
from kai_code.agent import KaiAgent


def test_add_system_message_to_graph():
    """Test that _add_system_message method exists and handles None graph gracefully."""
    agent = KaiAgent(root_dir=Path.cwd())

    # Before graph is initialized, should not crash
    agent._add_system_message("Test notification")

    # After graph is initialized, should not crash
    try:
        agent.run("Hello")  # Initialize the graph
        agent._add_system_message("Test notification")
        # If we get here without exception, the method works
        assert True
    except Exception as e:
        # The method should not cause exceptions
        pytest.fail(f"_add_system_message raised exception: {e}")
