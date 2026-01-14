"""Tests for subagent delegation functionality."""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from kai_code.subagents import (
    create_subagent_tool,
    load_subagents_from_config,
)


class TestCreateSubagentTool:
    """Tests for create_subagent_tool function."""

    def test_returns_tool(self):
        """Should return a LangChain BaseTool."""
        # Mock agent class
        mock_agent = Mock()

        tool = create_subagent_tool(
            agent=mock_agent,
            name="test-subagent",
            description="Test subagent",
            root_dir=Path.cwd(),
        )

        # Should be a tool with name and description
        assert hasattr(tool, "name")
        assert hasattr(tool, "description")
        # Should have invoke method (LangChain tool interface)
        assert hasattr(tool, "invoke")
        assert callable(tool.invoke)

    def test_tool_has_correct_name(self):
        """Tool should have the specified name."""
        mock_agent = Mock()

        tool = create_subagent_tool(
            agent=mock_agent,
            name="data-engineer",
            description="Data engineering specialist",
            root_dir=Path.cwd(),
        )

        assert tool.name == "data-engineer"

    def test_tool_has_correct_description(self):
        """Tool should have the specified description."""
        mock_agent = Mock()
        description = "Handles data pipelines and feature stores"

        tool = create_subagent_tool(
            agent=mock_agent,
            name="data-engineer",
            description=description,
            root_dir=Path.cwd(),
        )

        assert tool.description == description

    def test_tool_invokes_subagent(self):
        """Tool should create subagent instance and run task."""
        # Setup mock agent
        mock_agent_class = Mock()
        mock_agent_instance = Mock()
        mock_agent_instance.run.return_value = Mock(output="Task completed")
        mock_agent_class.return_value = mock_agent_instance

        tool = create_subagent_tool(
            agent=mock_agent_class,
            name="test-agent",
            description="Test",
            root_dir=Path.cwd(),
        )

        # Call the tool
        result = tool.invoke({"task": "Do something"})

        # Verify subagent was instantiated and run
        mock_agent_class.assert_called_once()
        mock_agent_instance.run.assert_called_once_with("Do something")

    def test_tool_returns_subagent_output(self):
        """Tool should return subagent's output."""
        mock_agent_class = Mock()
        mock_agent_instance = Mock()
        mock_agent_instance.run.return_value = Mock(output="Success!")
        mock_agent_class.return_value = mock_agent_instance

        tool = create_subagent_tool(
            agent=mock_agent_class,
            name="test-agent",
            description="Test",
            root_dir=Path.cwd(),
        )

        result = tool.invoke({"task": "Test task"})

        assert result == "Success!"


class TestLoadSubagentsFromConfig:
    """Tests for load_subagents_from_config function."""

    def test_returns_list_of_tools(self):
        """Should return a list of LangChain tools."""
        with patch("kai_code.agent_loader.load_agent") as mock_load:
            mock_agent_class = Mock()
            mock_load.return_value = mock_agent_class

            config = [
                {
                    "name": "agent1",
                    "description": "First agent",
                    "agent": "agent1",
                },
                {
                    "name": "agent2",
                    "description": "Second agent",
                    "agent": "agent2",
                },
            ]

            tools = load_subagents_from_config(
                subagent_configs=config,
                root_dir=Path.cwd(),
            )

            assert len(tools) == 2
            assert all(hasattr(t, "name") for t in tools)
            assert all(hasattr(t, "invoke") for t in tools)

    def test_empty_config_returns_empty_list(self):
        """Empty config should return empty list."""
        tools = load_subagents_from_config(
            subagent_configs=[],
            root_dir=Path.cwd(),
        )

        assert tools == []

    def test_skips_config_without_agent_ref(self):
        """Should skip configs that don't have an agent reference."""
        with patch("kai_code.agent_loader.load_agent") as mock_load:
            mock_agent_class = Mock()
            mock_load.return_value = mock_agent_class

            config = [
                {
                    "name": "valid-agent",
                    "description": "Has agent ref",
                    "agent": "valid-agent",
                },
                {
                    "name": "invalid-agent",
                    "description": "No agent ref",
                    # Missing 'agent' or 'ref' field
                },
            ]

            tools = load_subagents_from_config(
                subagent_configs=config,
                root_dir=Path.cwd(),
            )

            # Should only load the valid one
            assert len(tools) == 1
            assert tools[0].name == "valid-agent"

    def test_loads_agents_from_string_refs(self):
        """Should load agents from string references."""
        with patch("kai_code.agent_loader.load_agent") as mock_load:
            mock_agent_class = Mock()
            mock_load.return_value = mock_agent_class

            config = [
                {
                    "name": "data-engineer",
                    "description": "Data specialist",
                    "agent": "data-engineer",  # String ref
                },
            ]

            tools = load_subagents_from_config(
                subagent_configs=config,
                root_dir=Path.cwd(),
            )

            # Should have called load_agent with the string ref
            mock_load.assert_called_once_with("data-engineer")
            assert len(tools) == 1

    def test_uses_agent_class_directly(self):
        """Should use agent classes directly (not load from string)."""
        # Don't mock load_agent - test that it's not called
        with patch("kai_code.agent_loader.load_agent") as mock_load:
            mock_agent_class = Mock()

            config = [
                {
                    "name": "direct-agent",
                    "description": "Using class directly",
                    "agent": mock_agent_class,  # Pass class directly
                },
            ]

            tools = load_subagents_from_config(
                subagent_configs=config,
                root_dir=Path.cwd(),
            )

            # Should NOT have called load_agent
            mock_load.assert_not_called()
            assert len(tools) == 1

    def test_passes_model_to_create_subagent_tool(self):
        """Should pass model override to subagent tool."""
        with patch("kai_code.agent_loader.load_agent") as mock_load:
            with patch("kai_code.subagents.create_subagent_tool") as mock_create:
                mock_agent_class = Mock()
                mock_load.return_value = mock_agent_class
                mock_create.return_value = Mock()

                config = [
                    {
                        "name": "test-agent",
                        "description": "Test",
                        "agent": "test-agent",
                    },
                ]

                load_subagents_from_config(
                    subagent_configs=config,
                    root_dir=Path.cwd(),
                    model="opus",
                )

                # Should have called create_subagent_tool with model
                mock_create.assert_called_once()
                call_kwargs = mock_create.call_args.kwargs
                assert call_kwargs["model"] == "opus"
