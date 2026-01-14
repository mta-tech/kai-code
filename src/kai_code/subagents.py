"""Subagent support for deepagents-style delegation.

This module provides tools for wrapping subagents as callable tools
that main agents can delegate specialized tasks to.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from langchain_core.tools import BaseTool

if TYPE_CHECKING:
    from kai_code.agent import KaiAgent


def create_subagent_tool(
    agent: type["KaiAgent"],
    name: str,
    description: str,
    root_dir: Path,
    model: str | None = None,
) -> BaseTool:
    """Wrap a subagent as a callable tool (deepagents delegation pattern).

    This creates a LangChain tool that, when called, instantiates a fresh
    subagent and runs the delegated task. The subagent executes in an
    isolated context with its own state.

    Args:
        agent: The agent class to wrap (not an instance)
        name: Tool name for the subagent (e.g., "data-engineer")
        description: Description of what the subagent does
        root_dir: Working directory for subagent execution
        model: Model override (uses parent's model if None)

    Returns:
        A LangChain BaseTool that wraps the subagent

    Example:
        >>> from kai_code.agent_loader import load_agent
        >>> from kai_code.subagents import create_subagent_tool
        >>>
        >>> # Load a subagent class
        >>> DataEngineerAgent = load_agent("data-engineer")
        >>>
        >>> # Wrap as a tool
        >>> tool = create_subagent_tool(
        ...     agent=DataEngineerAgent,
        ...     name="data-engineer",
        ...     description="Handles data pipelines and feature stores",
        ...     root_dir=Path.cwd()
        ... )
        >>>
        >>> # Use in main agent's tool list
        >>> main_agent_tools = [tool, ...]
    """
    from langchain_core.tools import tool

    @tool(name)  # type: ignore[arg-type]
    def subagent_tool(task: str) -> str:
        """Delegate task to specialized subagent.

        Args:
            task: Detailed description of the task to delegate.

        Returns:
            Result from the subagent execution.
        """
        # Instantiate subagent with fresh context
        # Subagents don't use yolo mode (they should be deliberate)
        subagent_instance = agent(
            root_dir=root_dir,
            model=model or "sonnet",  # Default to sonnet if not specified
            yolo=False,
        )

        # Run the task
        result = subagent_instance.run(task)

        # Return output as string
        return str(result.output)

    # Set the tool description
    subagent_tool.description = description  # type: ignore[attr-defined]

    return subagent_tool  # type: ignore[return-value]


def load_subagents_from_config(
    subagent_configs: list[dict],
    root_dir: Path,
    model: str | None = None,
) -> list[BaseTool]:
    """Load subagents from configuration and wrap as tools.

    This processes a list of subagent definitions (typically from an
    agent's YAML frontmatter or configuration) and creates LangChain
    tools for each one.

    Args:
        subagent_configs: List of subagent configuration dicts
        root_dir: Working directory for subagent execution
        model: Model override for all subagents

    Returns:
        List of LangChain BaseTool instances wrapping the subagents

    Example:
        >>> config = [{
        ...     "name": "data-engineer",
        ...     "description": "Builds data pipelines",
        ...     "agent": "data-engineer"  # References .kai/agents/data-engineer.md
        ... }]
        >>>
        >>> tools = load_subagents_from_config(
        ...     subagent_configs=config,
        ...     root_dir=Path.cwd()
        ... )
    """
    from kai_code.agent_loader import load_agent

    tools = []

    for subagent_def in subagent_configs:
        # Get the agent reference (name or class)
        agent_ref = subagent_def.get("agent", subagent_def.get("ref"))
        if not agent_ref:
            continue

        # Load the subagent class
        # If agent_ref is a string, load it from .kai/agents/
        # If it's already a class, use it directly
        if isinstance(agent_ref, str):
            subagent_class = load_agent(agent_ref)
        else:
            subagent_class = agent_ref

        # Wrap as tool
        tool = create_subagent_tool(
            agent=subagent_class,
            name=subagent_def["name"],
            description=subagent_def.get("description", f"Subagent: {subagent_def['name']}"),
            root_dir=root_dir,
            model=model,
        )

        tools.append(tool)

    return tools
