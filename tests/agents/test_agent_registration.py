"""Tests for agent registration with ActiveAgentRegistry."""

import pytest
from pathlib import Path
from kai_code.agent import KaiAgent
from kai_code.tasks.active_agents import get_active_agent_registry


def test_agent_registers_on_init():
    registry = get_active_agent_registry()
    agent = KaiAgent(root_dir=Path.cwd())

    retrieved = registry.get(agent._agent_id)
    assert retrieved is agent


def test_agent_unregisters_on_shutdown():
    registry = get_active_agent_registry()
    agent = KaiAgent(root_dir=Path.cwd())
    agent_id = agent._agent_id

    agent.shutdown()

    assert registry.get(agent_id) is None
