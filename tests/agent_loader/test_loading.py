"""Tests for agent loading convenience functions."""
import pytest
from pathlib import Path
from kai_code.agent_loader import load_agent, list_agents
from kai_code.agent import KaiAgent


def test_load_agent_by_name(tmp_path):
    """Test loading an agent by name from .kai/agents/."""
    agents_dir = tmp_path / ".kai" / "agents"
    agents_dir.mkdir(parents=True)

    # Create an agent file
    (agents_dir / "test-agent.md").write_text("""---
name: test-agent
description: Test agent
---

Test prompt.
""")

    agent = load_agent("test-agent", agents_dir=agents_dir, root_dir=tmp_path)

    assert isinstance(agent, KaiAgent)


def test_load_nonexistent_agent_raises_error(tmp_path):
    """Test loading nonexistent agent raises FileNotFoundError."""
    agents_dir = tmp_path / ".kai" / "agents"
    agents_dir.mkdir(parents=True)

    with pytest.raises(FileNotFoundError, match="not found"):
        load_agent("nonexistent", agents_dir=agents_dir)


def test_list_agents(tmp_path):
    """Test listing all available agents."""
    agents_dir = tmp_path / ".kai" / "agents"
    agents_dir.mkdir(parents=True)

    # Create multiple agent files
    (agents_dir / "agent-one.md").write_text("---\nname: agent-one\n---\n")
    (agents_dir / "agent-two.md").write_text("---\nname: agent-two\n---\n")
    (agents_dir / "not-an-agent.txt").write_text("text file")

    agents = list_agents(agents_dir)

    assert "agent-one" in agents
    assert "agent-two" in agents
    assert "not-an-agent" not in agents


def test_load_agent_uses_default_directory(tmp_path, monkeypatch):
    """Test load_agent uses .kai/agents by default."""
    # Change to temp directory
    monkeypatch.chdir(tmp_path)

    # Create default agents directory
    agents_dir = tmp_path / ".kai" / "agents"
    agents_dir.mkdir(parents=True)

    agent_file = agents_dir / "default-test.md"
    agent_file.write_text("---\nname: default-test\n---\n")

    # Load without specifying directory
    agent = load_agent("default-test", root_dir=tmp_path)

    assert isinstance(agent, KaiAgent)
