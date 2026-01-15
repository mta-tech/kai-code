"""Tests for ActiveAgentRegistry."""

import pytest
from pathlib import Path
from kai_code.agent import KaiAgent
from kai_code.tasks.active_agents import ActiveAgentRegistry, get_active_agent_registry


def test_registry_is_singleton():
    registry1 = get_active_agent_registry()
    registry2 = get_active_agent_registry()
    assert registry1 is registry2


def test_register_and_lookup():
    registry = ActiveAgentRegistry()
    agent = KaiAgent(root_dir=Path.cwd())

    registry.register("agent-1", agent)
    retrieved = registry.get("agent-1")
    assert retrieved is agent


def test_unregister():
    registry = ActiveAgentRegistry()
    agent = KaiAgent(root_dir=Path.cwd())

    registry.register("agent-1", agent)
    registry.unregister("agent-1")

    assert registry.get("agent-1") is None


def test_list_all():
    registry = ActiveAgentRegistry()
    agent1 = KaiAgent(root_dir=Path.cwd())
    agent2 = KaiAgent(root_dir=Path.cwd())

    registry.register("agent-1", agent1)
    registry.register("agent-2", agent2)

    agents = registry.list_all()
    assert len(agents) == 2
    assert agent1 in agents
    assert agent2 in agents
