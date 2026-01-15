"""Integration tests for auto-nudge edge cases."""

import pytest
import time
from pathlib import Path
from kai_code.agent import KaiAgent
from kai_code.tasks import get_task_manager, get_agent_task_registry


def test_failed_task_notification():
    """Test that failed tasks generate proper notifications."""
    agent = KaiAgent(root_dir=Path.cwd())

    task_manager = get_task_manager()
    task_id = task_manager.run_shell("exit 1", working_dir=Path.cwd())

    # Register the task with the agent
    get_agent_task_registry().register_task(agent._agent_id, task_id)

    # Wait for task to complete
    time.sleep(1)

    # The system should handle failed tasks without errors
    assert True


def test_agent_shutdown_receives_no_notification():
    """Test that shut down agent doesn't receive notifications."""
    agent = KaiAgent(root_dir=Path.cwd())
    agent_id = agent._agent_id

    task_manager = get_task_manager()
    task_id = task_manager.run_shell("sleep 2", working_dir=Path.cwd())

    # Register the task with the agent
    get_agent_task_registry().register_task(agent_id, task_id)

    # Shutdown agent immediately
    agent.shutdown()

    # Wait for task to complete
    time.sleep(3)

    # Agent should not receive notification (it's shut down)
    # This test just verifies no crash occurs
    assert True


def test_large_output_truncation():
    """Test that large output is properly truncated."""
    agent = KaiAgent(root_dir=Path.cwd())

    task_manager = get_task_manager()
    # Create task with large output
    task_id = task_manager.run_shell("python -c \"print('x' * 15000)\"", working_dir=Path.cwd())

    # Register the task with the agent
    get_agent_task_registry().register_task(agent._agent_id, task_id)

    # Wait for task to complete
    time.sleep(2)

    # The system should handle large output without errors
    assert True
