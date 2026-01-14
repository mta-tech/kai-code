"""Tests for SeeknalAgent migration to hybrid model."""

from pathlib import Path

from kai_code.agent_loader import load_agent
from kai_code.agents.seeknal.agent import SeeknalAgent
from kai_code.prompts import load_prompt, clear_cache


class TestSeeknalAgentMigration:
    """Tests for SeeknalAgent Python and markdown equivalence."""

    def test_python_agent_uses_kai_seeknal_prompt(self):
        """Python SeeknalAgent should use kai-seeknal prompt."""
        agent = SeeknalAgent(root_dir=Path.cwd())
        prompt_name = agent._get_base_prompt_name()
        assert prompt_name == "kai-seeknal"

    def test_markdown_agent_extends_kai_seeknal(self):
        """Markdown seeknal.md should extend kai-seeknal."""
        clear_cache()

        from kai_code.agent_definition import AgentDefinition

        definition = AgentDefinition(Path(".kai/agents/seeknal.md"))
        assert definition.extends == "kai-seeknal"

    def test_markdown_agent_compiles_successfully(self):
        """seeknal.md should load and instantiate successfully."""
        from kai_code.agent import KaiAgent

        agent = load_agent("seeknal")
        assert agent is not None
        # The loaded agent is a dynamic class inheriting from KaiAgent
        assert isinstance(agent, KaiAgent)
        # The class name should reflect the agent name
        assert agent.__class__.__name__ == "Seeknal"

    def test_both_paths_use_same_base_prompt(self):
        """Both Python and markdown paths should use kai-seeknal."""
        clear_cache()

        # Load prompt via Python agent's prompt name
        python_prompt = load_prompt("kai-seeknal")

        # Load prompt via markdown agent's name
        markdown_prompt = load_prompt("seeknal")

        # Both should include kai-seeknal content
        # (markdown extends kai-seeknal, so it should be a superset)
        assert "Seeknal" in python_prompt
        assert "Seeknal" in markdown_prompt

        # Markdown prompt should be longer (extends base)
        assert len(markdown_prompt) >= len(python_prompt)

    def test_seeknal_agent_tools_loaded(self):
        """SeeknalAgent should have Seeknal tools available."""
        agent = SeeknalAgent(root_dir=Path.cwd())
        tools = agent._get_subclass_tools()

        # Should have Seeknal-specific tools
        tool_names = [t.name for t in tools]
        seeknal_tools = [t for t in tool_names if "seeknal" in t.lower() or any(x in t.lower() for x in ["project", "flow", "entity", "feature", "version"])]

        # Should have some Seeknal tools
        assert len(seeknal_tools) > 0

    def test_markdown_agent_has_kaiagent_base(self):
        """Markdown-compiled agent should inherit from KaiAgent."""
        from kai_code.agent import KaiAgent

        agent = load_agent("seeknal")

        # Should be an instance of KaiAgent
        assert isinstance(agent, KaiAgent)

        # Should have the same interface as Python SeeknalAgent
        assert hasattr(agent, 'run')
        assert hasattr(agent, '_get_base_prompt_name')
        assert hasattr(agent, '_get_subclass_tools')

    def test_both_agents_are_seeknal_agents(self):
        """Both Python and markdown agents should be KaiAgent instances."""
        from kai_code.agent import KaiAgent

        # Python path
        python_agent = SeeknalAgent(root_dir=Path.cwd())
        assert isinstance(python_agent, KaiAgent)

        # Markdown path
        markdown_agent = load_agent("seeknal")
        assert isinstance(markdown_agent, KaiAgent)
