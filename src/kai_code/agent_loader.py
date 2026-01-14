"""Agent loading utilities.

This module provides functions to load and instantiate agents from
markdown definition files.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from kai_code.agent import KaiAgent
from kai_code.agent_definition import AgentDefinition


def load_agent(
    name: str,
    agents_dir: Path | str | None = None,
    root_dir: Path | str | None = None,
    **kwargs: Any,
) -> KaiAgent:
    """Load an agent from markdown definition.

    Args:
        name: Agent name (kebab-case, matches .md filename without extension)
        agents_dir: Directory containing agent definitions (default: .kai/agents/)
        root_dir: Project root directory (default: current working directory)
        **kwargs: Additional arguments passed to agent constructor

    Returns:
        Initialized KaiAgent instance

    Raises:
        FileNotFoundError: If agent definition file doesn't exist

    Example:
        >>> agent = load_agent('seeknal-data-engineer')
        >>> result = agent.run("Create a feature group")
    """
    # Determine agents directory
    if agents_dir is None:
        # Use default .kai/agents from root_dir or cwd
        if root_dir is None:
            root_dir = Path.cwd()
        else:
            root_dir = Path(root_dir)
        agents_dir = root_dir / ".kai" / "agents"
    else:
        agents_dir = Path(agents_dir)
        if root_dir is None:
            root_dir = Path.cwd()
        else:
            root_dir = Path(root_dir)

    # Find agent file
    agent_path = agents_dir / f"{name}.md"
    if not agent_path.exists():
        raise FileNotFoundError(
            f"Agent '{name}' not found at {agent_path}. "
            f"Available agents: {list_agents(agents_dir)}"
        )

    # Parse definition
    definition = AgentDefinition(agent_path)

    # Note: The 'extends' field references a prompt (e.g., 'kai-seeknal'), not another agent definition.
    # Inheritance is handled at the prompt level by the prompt loader when the agent calls
    # _get_base_prompt_name(), which returns the agent's name. The prompt loader then:
    # 1. Finds the agent definition file (e.g., .kai/agents/seeknal.md)
    # 2. Parses the 'extends' field
    # 3. Loads the parent prompt and merges with the agent's specialized content
    # This means agent definitions extend prompts, not other agent definitions.

    # Compile to class and instantiate
    agent_class = definition.to_agent_class()
    agent = agent_class(root_dir=root_dir, **kwargs)

    return agent


def list_agents(agents_dir: Path | str | None = None) -> list[str]:
    """List all available agent definitions.

    Args:
        agents_dir: Directory containing agent definitions (default: .kai/agents/)

    Returns:
        List of agent names (kebab-case, without .md extension)

    Example:
        >>> list_agents()
        ['seeknal', 'seeknal-data-engineer', 'dbt-analyst']
    """
    if agents_dir is None:
        agents_dir = Path.cwd() / ".kai" / "agents"
    else:
        agents_dir = Path(agents_dir)

    if not agents_dir.exists():
        return []

    agents = []
    for agent_file in agents_dir.glob("*.md"):
        # Skip files starting with underscore
        if agent_file.name.startswith('_'):
            continue
        agents.append(agent_file.stem)

    return sorted(agents)
