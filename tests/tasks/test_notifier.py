"""Tests for TaskCompletionNotifier."""

import pytest
from unittest.mock import Mock
from kai_code.tasks.task import Task, TaskStatus
from kai_code.tasks.notifier import TaskCompletionNotifier
from kai_code.tasks.registry import AgentTaskRegistry
from kai_code.tasks.active_agents import ActiveAgentRegistry


def test_notifier_formats_completion_message():
    agent_registry = AgentTaskRegistry()
    active_agents = ActiveAgentRegistry()
    notifier = TaskCompletionNotifier(agent_registry, active_agents)

    task = Mock(spec=Task)
    task.id = "test-123"
    task.description = "Test task"
    task.type = "shell"
    task.status = TaskStatus.COMPLETED
    task.duration = 5.5
    task.error = None
    task.output = "Hello World"

    message = notifier._format_completion_message(task)

    assert "Background task completed:" in message
    assert "Task ID: test-123" in message
    assert "Status: completed" in message
    assert "Duration: 5.5s" in message
    assert "Hello World" in message


def test_notifier_formats_failed_task():
    agent_registry = AgentTaskRegistry()
    active_agents = ActiveAgentRegistry()
    notifier = TaskCompletionNotifier(agent_registry, active_agents)

    task = Mock(spec=Task)
    task.id = "test-456"
    task.description = "Failed task"
    task.type = "shell"
    task.status = TaskStatus.FAILED
    task.duration = 2.0
    task.error = "Command failed with exit code 1"
    task.output = "Error output"

    message = notifier._format_completion_message(task)

    assert "Status: failed" in message
    assert "Error: Command failed with exit code 1" in message


def test_notifier_truncates_large_output():
    agent_registry = AgentTaskRegistry()
    active_agents = ActiveAgentRegistry()
    notifier = TaskCompletionNotifier(agent_registry, active_agents)

    task = Mock(spec=Task)
    task.id = "test-789"
    task.description = "Large output task"
    task.type = "shell"
    task.status = TaskStatus.COMPLETED
    task.duration = 10.0
    task.error = None
    task.output = "x" * 15000  # 15K characters

    message = notifier._format_completion_message(task)

    assert len(message) < 12000  # Should be truncated
    assert "output truncated" in message
    assert "get_task_output('test-789')" in message


def test_notifier_skips_unknown_task():
    agent_registry = AgentTaskRegistry()
    active_agents = ActiveAgentRegistry()
    notifier = TaskCompletionNotifier(agent_registry, active_agents)

    task = Mock(spec=Task)
    task.id = "unknown-123"
    task.status = TaskStatus.COMPLETED

    # Should not raise exception
    notifier(task)

    # Nothing should happen (no agent to notify)
    assert True


def test_notifier_skips_when_agent_not_found():
    agent_registry = AgentTaskRegistry()
    active_agents = ActiveAgentRegistry()
    notifier = TaskCompletionNotifier(agent_registry, active_agents)

    # Register task but agent not in active_agents
    agent_registry.register_task("ghost-agent", "ghost-123")

    task = Mock(spec=Task)
    task.id = "ghost-123"
    task.status = TaskStatus.COMPLETED

    # Should not raise exception
    notifier(task)
