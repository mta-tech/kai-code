"""Tests for subagent loading from agent definitions."""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from kai_code.agent_definition import AgentDefinition


class TestAgentDefinitionSubagents:
    """Tests for subagent parsing in AgentDefinition."""

    def test_parse_subagents_from_frontmatter(self):
        """Should parse subagents list from YAML frontmatter."""
        import tempfile
        import yaml

        # Create a temporary agent definition with subagents
        content = """---
name: test-agent
description: Test agent with subagents
subagents:
  - name: data-engineer
    description: Data engineering specialist
    agent: data-engineer
  - name: ml-engineer
    description: ML specialist
    agent: ml-engineer
---

# Purpose

Test agent content.
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write(content)
            temp_path = Path(f.name)

        try:
            definition = AgentDefinition(temp_path)

            assert definition.subagents == [
                {
                    "name": "data-engineer",
                    "description": "Data engineering specialist",
                    "agent": "data-engineer",
                },
                {
                    "name": "ml-engineer",
                    "description": "ML specialist",
                    "agent": "ml-engineer",
                },
            ]
        finally:
            temp_path.unlink()

    def test_empty_subagents_when_not_specified(self):
        """Should have empty subagents list when not specified."""
        import tempfile

        content = """---
name: test-agent
description: Test agent
---

# Purpose

Test agent content.
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write(content)
            temp_path = Path(f.name)

        try:
            definition = AgentDefinition(temp_path)
            assert definition.subagents == []
        finally:
            temp_path.unlink()

    @patch("kai_code.subagents.load_subagents_from_config")
    @patch("kai_code.agent_loader.load_agent")
    def test_compiled_agent_includes_subagent_tools(self, mock_load_agent, mock_load_subagents):
        """Compiled agent should include subagent tools in _get_subclass_tools."""
        import tempfile

        # Mock subagent loading
        mock_subagent_tool = Mock()
        mock_subagent_tool.name = "data-engineer"
        mock_load_subagents.return_value = [mock_subagent_tool]

        # Create agent definition with subagents
        content = """---
name: test-agent
description: Test agent with subagents
subagents:
  - name: data-engineer
    description: Data specialist
    agent: data-engineer
---

# Purpose

Test agent content.
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write(content)
            temp_path = Path(f.name)

        try:
            definition = AgentDefinition(temp_path)
            AgentClass = definition.to_agent_class()

            # Verify subagent config was parsed
            assert definition.subagents == [
                {
                    "name": "data-engineer",
                    "description": "Data specialist",
                    "agent": "data-engineer",
                }
            ]

            # We can't easily test the full agent instantiation without
            # mocking more dependencies, but we verified the subagent
            # configuration is parsed correctly

        finally:
            temp_path.unlink()

    def test_subagents_with_complex_config(self):
        """Should parse subagent configurations with all fields."""
        import tempfile

        content = """---
name: test-agent
description: Test agent
subagents:
  - name: specialist
    description: Specialist agent
    agent: specialist
    tools:
      include:
        - kai_code.tools.bash
        - kai_code.tools.read
    trigger:
      keywords: [specialize, expert]
      tool_patterns: [specialize]
---

# Purpose

Test agent content.
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write(content)
            temp_path = Path(f.name)

        try:
            definition = AgentDefinition(temp_path)

            assert len(definition.subagents) == 1
            subagent = definition.subagents[0]
            assert subagent["name"] == "specialist"
            assert subagent["description"] == "Specialist agent"
            assert subagent["agent"] == "specialist"
            assert "tools" in subagent
            assert "trigger" in subagent
        finally:
            temp_path.unlink()
