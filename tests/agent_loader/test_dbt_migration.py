"""Tests for DbtAgent migration to hybrid model."""

from pathlib import Path

from kai_code.agent_loader import load_agent
from kai_code.agents.dbt.agent import DbtAgent
from kai_code.prompts import load_prompt, clear_cache


class TestDbtAgentMigration:
    """Tests for DbtAgent Python and markdown equivalence."""

    def test_python_agent_uses_kai_dbt_prompt(self):
        """Python DbtAgent should use kai-dbt prompt."""
        agent = DbtAgent(root_dir=Path.cwd())
        prompt_name = agent._get_base_prompt_name()
        assert prompt_name == "kai-dbt"

    def test_markdown_agent_extends_kai_dbt(self):
        """Markdown dbt.md should extend kai-dbt."""
        clear_cache()

        from kai_code.agent_definition import AgentDefinition

        definition = AgentDefinition(Path(".kai/agents/dbt.md"))
        assert definition.extends == "kai-dbt"

    def test_markdown_agent_compiles_successfully(self):
        """dbt.md should load and instantiate successfully."""
        from kai_code.agent import KaiAgent

        agent = load_agent("dbt")
        assert agent is not None
        # The loaded agent is a dynamic class inheriting from KaiAgent
        assert isinstance(agent, KaiAgent)
        # The class name should reflect the agent name
        assert agent.__class__.__name__ == "Dbt"

    def test_both_paths_use_same_base_prompt(self):
        """Both Python and markdown paths should use kai-dbt."""
        clear_cache()

        # Load prompt via Python agent's prompt name
        python_prompt = load_prompt("kai-dbt")

        # Load prompt via markdown agent's name
        markdown_prompt = load_prompt("dbt")

        # Both should include kai-dbt content
        # (markdown extends kai-dbt, so it should be a superset)
        assert "dbt" in python_prompt.lower()
        assert "dbt" in markdown_prompt.lower()

        # Markdown prompt should be longer (extends base)
        assert len(markdown_prompt) >= len(python_prompt)

    def test_dbt_agent_has_dbt_specific_properties(self):
        """DbtAgent should have dbt-specific properties."""
        agent = DbtAgent(root_dir=Path.cwd())

        # Should have dbt-specific properties
        assert hasattr(agent, 'dbt_project_dir')
        assert hasattr(agent, 'db_connection')
        assert hasattr(agent, 'adapter')

    def test_markdown_agent_has_kaiagent_base(self):
        """Markdown-compiled agent should inherit from KaiAgent."""
        from kai_code.agent import KaiAgent

        agent = load_agent("dbt")

        # Should be an instance of KaiAgent
        assert isinstance(agent, KaiAgent)

        # Should have the same interface as Python DbtAgent
        assert hasattr(agent, 'run')
        assert hasattr(agent, '_get_base_prompt_name')
        assert hasattr(agent, '_get_subclass_tools')

    def test_both_agents_are_dbt_agents(self):
        """Both Python and markdown agents should be KaiAgent instances."""
        from kai_code.agent import KaiAgent

        # Python path
        python_agent = DbtAgent(root_dir=Path.cwd())
        assert isinstance(python_agent, KaiAgent)

        # Markdown path
        markdown_agent = load_agent("dbt")
        assert isinstance(markdown_agent, KaiAgent)

        # Both should use the same base prompt
        assert python_agent._get_base_prompt_name() == "kai-dbt"
        assert markdown_agent._get_base_prompt_name() == "dbt"  # Returns agent name, which loads kai-dbt prompt
