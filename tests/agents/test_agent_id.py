"""Tests for agent_id attribute on KaiAgent."""

import pytest
from pathlib import Path
from kai_code.agent import KaiAgent


def test_agent_has_unique_id():
    agent1 = KaiAgent(root_dir=Path.cwd())
    agent2 = KaiAgent(root_dir=Path.cwd())

    assert agent1._agent_id is not None
    assert agent2._agent_id is not None
    assert agent1._agent_id != agent2._agent_id
    assert len(agent1._agent_id) == 8  # UUID prefix
