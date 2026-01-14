"""Agent compilation and validation commands."""

from pathlib import Path
from typing import Any

from ..agent_definition import AgentDefinition


def validate_agent(agent_path: str | Path) -> list[str]:
    """Validate an agent definition file.

    Args:
        agent_path: Path to agent definition file.

    Returns:
        List of validation errors (empty if valid).
    """
    errors = []
    agent_path = Path(agent_path)

    # Check file exists
    if not agent_path.exists():
        errors.append(f"File not found: {agent_path}")
        return errors

    # Check file extension
    if agent_path.suffix != ".md":
        errors.append(f"Agent file must have .md extension, got: {agent_path.suffix}")

    try:
        definition = AgentDefinition(agent_path)
    except Exception as e:
        errors.append(f"Failed to parse agent definition: {e}")
        return errors

    # Validate name
    if not definition.name:
        errors.append("Agent name is empty")

    # Validate name is kebab-case
    if definition.name:
        if not all(c.islower() or c.isdigit() or c == "-" for c in definition.name):
            errors.append(
                f"Agent name must be kebab-case (lowercase, numbers, hyphens), got: {definition.name}"
            )

        if definition.name.startswith("-") or definition.name.endswith("-"):
            errors.append("Agent name cannot start or end with hyphen")

        if "--" in definition.name:
            errors.append("Agent name cannot contain consecutive hyphens")

    # Validate description
    if not definition.description:
        errors.append("Agent description is required")

    # Validate model
    if definition.model and definition.model not in ["inherit", "sonnet", "opus", "haiku"]:
        errors.append(
            f"Model must be one of: inherit, sonnet, opus, haiku; got: {definition.model}"
        )

    # Validate tools
    if definition.tools:
        if not isinstance(definition.tools, list):
            errors.append(f"Tools must be a list, got: {type(definition.tools)}")

    # Validate extends references a valid prompt
    if definition.extends:
        from ..prompts import get_prompt_path

        try:
            get_prompt_path(definition.extends)
        except FileNotFoundError:
            errors.append(f"Parent prompt not found: {definition.extends}")

    return errors


def compile_agent_to_string(agent_path: str | Path) -> str:
    """Compile an agent definition to Python class code.

    Args:
        agent_path: Path to agent definition file.

    Returns:
        Python class code as string.
    """
    agent_path = Path(agent_path)
    definition = AgentDefinition(agent_path)
    agent_class = definition.to_agent_class()

    # Generate Python code representation
    code = f'''"""Auto-generated agent class from {agent_path.name}"""

from kai_code.agent import KaiAgent
from typing import List

{agent_class.__name__} = agent_class

class {agent_class.__name__}(KaiAgent):
    """{definition.description}"""

    def _get_base_prompt_name(self) -> str:
        return "{definition.name}"

    def _get_subclass_tools(self) -> List:
        from kai_code.tool_loader import load_tools_from_patterns

        tools = load_tools_from_patterns({definition.tools})
'''

    return code


def get_agent_info(agent_path: str | Path) -> dict[str, Any]:
    """Get detailed information about an agent definition.

    Args:
        agent_path: Path to agent definition file.

    Returns:
        Dictionary with agent information.
    """
    agent_path = Path(agent_path)
    definition = AgentDefinition(agent_path)

    # Count prompt lines
    prompt_lines = definition.system_prompt.strip().splitlines()

    # Get tool count
    from kai_code.tool_loader import load_tools_from_patterns

    tool_count = 0
    if definition.tools:
        try:
            tool_count = len(load_tools_from_patterns(definition.tools))
        except Exception:
            tool_count = -1  # Error loading tools

    return {
        "name": definition.name,
        "description": definition.description,
        "extends": definition.extends,
        "model": definition.model,
        "tools": definition.tools if definition.tools else [],
        "tool_count": tool_count,
        "color": getattr(definition, "color", None),
        "prompt_lines": len(prompt_lines),
        "file_path": str(agent_path),
        "file_size": agent_path.stat().st_size,
    }
