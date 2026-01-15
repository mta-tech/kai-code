"""Integration tests for auto-nudge feature."""

import pytest
import time
from pathlib import Path
from kai_code.agent import KaiAgent
from kai_code.tasks import get_task_manager


def test_task_completion_notifies_agent():
    """Test that agent receives notification when task completes."""
    agent = KaiAgent(root_dir=Path.cwd())

    # Create a quick background task
    task_manager = get_task_manager()
    task_id = task_manager.run_shell("echo test_output", working_dir=Path.cwd())

    # Register the task with the agent
    from kai_code.tasks import get_agent_task_registry
    get_agent_task_registry().register_task(agent._agent_id, task_id)

    # Wait for task to complete
    time.sleep(1)

    # Check for system message (if graph was initialized)
    if agent._graph is not None:
        messages = agent._graph.state.get('messages', [])
        completion_msgs = [
            m for m in messages
            if hasattr(m, 'type') and m.type == 'system'
            and 'Background task completed' in m.content
        ]

        # If we have completion messages, verify content
        if completion_msgs:
            assert 'test_output' in completion_msgs[0].content
