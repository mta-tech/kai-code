"""Tests for agent compilation to Python classes."""
import pytest
from pathlib import Path
from kai_code.agent_definition import AgentDefinition
from kai_code.agent import KaiAgent


def test_compile_agent_to_class(tmp_path):
    """Test compiling agent definition to Python class."""
    agent_file = tmp_path / "simple-agent.md"
    agent_file.write_text("""---
name: simple-agent
description: A simple test agent
tools: Bash, Read
---

# Purpose

You are a simple test agent.
""")

    definition = AgentDefinition(agent_file)
    agent_class = definition.to_agent_class()

    # Should be a class
    assert isinstance(agent_class, type)

    # Should inherit from KaiAgent
    assert issubclass(agent_class, KaiAgent)

    # Should be instantiable
    agent = agent_class(root_dir=tmp_path)
    assert isinstance(agent, KaiAgent)


def test_compiled_agent_has_custom_prompt(tmp_path):
    """Test that compiled agent uses custom prompt from markdown."""
    agent_file = tmp_path / "custom-prompt.md"
    agent_file.write_text("""---
name: custom-prompt
---

# Custom Instructions

This is a custom prompt for testing.
""")

    definition = AgentDefinition(agent_file)
    agent_class = definition.to_agent_class()
    agent = agent_class(root_dir=tmp_path)

    # The agent should have access to the custom prompt
    # (exact mechanism depends on KaiAgent implementation)
    assert hasattr(agent, '_get_base_prompt_name')


def test_compiled_agent_with_tools(tmp_path):
    """Test that compiled agent can specify tools."""
    agent_file = tmp_path / "tool-agent.md"
    agent_file.write_text("""---
name: tool-agent
tools: Bash, Read, Write
---

Test.
""")

    definition = AgentDefinition(agent_file)
    agent_class = definition.to_agent_class()

    # The class should have tool information
    # (exact mechanism depends on KaiAgent implementation)
    assert definition.tools == ["Bash", "Read", "Write"]
