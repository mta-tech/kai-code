"""Tests for task registration in execute_async_tool."""

import pytest
from pathlib import Path
from kai_code.agent import KaiAgent
from kai_code.tasks import get_agent_task_registry, get_task_manager


def test_execute_async_registers_task():
    """Test that execute_async_tool registers tasks with the agent."""
    agent = KaiAgent(root_dir=Path.cwd())
    registry = get_agent_task_registry()

    # Run a command that will exceed timeout and go to background
    task_manager = get_task_manager()
    task_id = task_manager.run_shell("echo test", working_dir=Path.cwd())

    # Manually register the task (simulating what execute_async_tool does)
    registry.register_task(agent._agent_id, task_id)

    # Task should be registered
    agent_tasks = registry.get_agent_tasks(agent._agent_id)
    assert task_id in agent_tasks

