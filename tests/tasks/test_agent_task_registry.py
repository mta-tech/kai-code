"""Tests for AgentTaskRegistry."""

import pytest
from kai_code.tasks.registry import AgentTaskRegistry


def test_registry_initially_empty():
    registry = AgentTaskRegistry()
    assert registry.get_agent_id("nonexistent") is None


def test_register_and_lookup():
    registry = AgentTaskRegistry()
    registry.register_task("agent-1", "task-1")
    assert registry.get_agent_id("task-1") == "agent-1"


def test_multiple_tasks_per_agent():
    registry = AgentTaskRegistry()
    registry.register_task("agent-1", "task-1")
    registry.register_task("agent-1", "task-2")
    tasks = registry.get_agent_tasks("agent-1")
    assert tasks == {"task-1", "task-2"}


def test_cleanup_agent_tasks():
    registry = AgentTaskRegistry()
    registry.register_task("agent-1", "task-1")
    registry.register_task("agent-1", "task-2")
    registry.cleanup_agent_tasks("agent-1")
    assert registry.get_agent_id("task-1") is None
    assert registry.get_agent_tasks("agent-1") == set()


def test_unregister_task():
    registry = AgentTaskRegistry()
    registry.register_task("agent-1", "task-1")
    registry.unregister_task("task-1")
    assert registry.get_agent_id("task-1") is None
