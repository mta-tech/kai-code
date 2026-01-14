"""Tests for AgentDefinition class."""
import pytest
from pathlib import Path
from kai_code.agent_definition import AgentDefinition


def test_parse_agent_with_full_frontmatter(tmp_path):
    """Test parsing agent with complete YAML frontmatter."""
    # Create test agent file
    agent_file = tmp_path / "test-agent.md"
    agent_file.write_text("""---
name: test-agent
description: Test agent for unit testing
tools: Bash, Read, Write
model: sonnet
extends: kai-code
---

# Purpose

You are a test agent.
""")

    # Parse the agent
    definition = AgentDefinition(agent_file)

    assert definition.name == "test-agent"
    assert definition.description == "Test agent for unit testing"
    assert definition.tools == ["Bash", "Read", "Write"]
    assert definition.model == "sonnet"
    assert definition.extends == "kai-code"
    assert "You are a test agent" in definition.system_prompt


def test_parse_agent_minimal_frontmatter(tmp_path):
    """Test parsing agent with minimal frontmatter (defaults)."""
    agent_file = tmp_path / "minimal-agent.md"
    agent_file.write_text("""---
name: minimal-agent
---

Minimal prompt.
""")

    definition = AgentDefinition(agent_file)

    assert definition.name == "minimal-agent"
    assert definition.description == ""
    assert definition.tools == []
    assert definition.model is None
    assert definition.extends is None
    assert definition.system_prompt == "Minimal prompt."


def test_parse_agent_without_frontmatter(tmp_path):
    """Test parsing agent without frontmatter (uses filename)."""
    agent_file = tmp_path / "no-frontmatter.md"
    agent_file.write_text("Just the prompt body.")

    definition = AgentDefinition(agent_file)

    assert definition.name == "no-frontmatter"
    assert definition.metadata == {}
    assert definition.system_prompt == "Just the prompt body."


def test_parse_agent_allowed_tools_field(tmp_path):
    """Test parsing agent with allowed-tools instead of tools."""
    agent_file = tmp_path / "allowed-tools-agent.md"
    agent_file.write_text("""---
name: allowed-tools-agent
allowed-tools: Bash, Read
---

Test.
""")

    definition = AgentDefinition(agent_file)

    assert definition.allowed_tools == ["Bash", "Read"]
    assert definition.tools == []


def test_invalid_agent_name_format(tmp_path):
    """Test validation rejects invalid agent names."""
    # Agent names must be kebab-case
    agent_file = tmp_path / "InvalidName.md"
    agent_file.write_text("""---
name: InvalidName
---

Test.
""")

    with pytest.raises(ValueError, match="kebab-case"):
        AgentDefinition(agent_file)
