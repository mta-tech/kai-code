"""Skill loading tools - dynamic skill management.

Ported from letta-code Skill tool implementation.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, List, Optional

from langchain_core.tools import tool

from ..errors import ActionableError, ErrorType
from ..error_suggestions import make_skill_not_found_error, suggest_values
from ..skills_parser import parse_skill_metadata
from ..skills import initialize_skills_system

logger = logging.getLogger(__name__)


def _format_error_for_tool(error: ActionableError) -> str:
    """Format an ActionableError as a readable string for tool output.

    Since tools return strings to the LLM agent, we format the error
    as plain text that the agent can understand and act upon.

    Args:
        error: The ActionableError to format.

    Returns:
        A formatted string representation of the error.
    """
    lines = [f"Error ({error.error_type.value}): {error.message}"]

    if error.suggestions:
        lines.append("\nSuggestions:")
        for suggestion in error.suggestions:
            lines.append(f"  • {suggestion}")

    if error.related_items:
        lines.append(f"\nDid you mean: {', '.join(error.related_items)}")

    if error.recovery_commands:
        lines.append("\nTry these commands:")
        for cmd in error.recovery_commands:
            if not cmd.startswith("#"):
                lines.append(f"  $ {cmd}")

    return "\n".join(lines)


@tool
def load_skill(skill: str) -> str:
    """Load a skill into loaded_skills memory block.

    Args:
        skill: The skill ID to load (e.g., "data-analysis", "web-scraper")

    Returns:
        Confirmation message with skill details
    """
    try:
        # Get agent instance - tools need access to agent's memory manager
        from ..agent import KaiAgent
        # This is a bit of a hack - we need to get the current agent
        # In a real implementation, this would be injected or passed via context
        agent = _get_current_agent_instance()

        if not agent:
            error = ActionableError(
                error_type=ErrorType.AGENT_NOT_FOUND,
                message="No active agent found",
                suggestions=[
                    "Ensure an agent session is active before loading skills",
                    "Start a new conversation to initialize the agent",
                ],
                recovery_commands=["/help"],
                severity="warning",
            )
            return _format_error_for_tool(error)

        # Get memory manager and skills directory
        memory_manager = getattr(agent, '_memory_manager', None)
        if not memory_manager:
            error = ActionableError(
                error_type=ErrorType.SKILL_LOAD_ERROR,
                message="Memory management not available",
                suggestions=[
                    "The agent was not initialized with skill support",
                    "Check if skills are enabled in your configuration",
                ],
                recovery_commands=["/skills"],
                severity="warning",
            )
            return _format_error_for_tool(error)

        skills_dir = getattr(agent, '_config', None)
        skills_directory = skills_dir.skills_dir if skills_dir else ".skills"

        # Discover skills to find the requested skill
        from ..skills_parser import discover_skills
        result = discover_skills(agent._config.root_dir, skills_directory)

        # Get list of available skill IDs
        available_skill_ids = [s.skill_id for s in result.skills]

        # Find the skill by ID
        skill_metadata = None
        for s in result.skills:
            if s.skill_id == skill:
                skill_metadata = s
                break

        if not skill_metadata:
            # Use make_skill_not_found_error for rich suggestions
            error = make_skill_not_found_error(skill, available_skill_ids)
            return _format_error_for_tool(error)

        # Check if already loaded
        loaded_block = memory_manager.get_loaded_skills_block()
        if loaded_block and skill in loaded_block.loaded_skills:
            return f"Skill '{skill}' is already loaded"

        # Load skill content
        skill_content = skill_metadata.path.read_text(encoding='utf-8')

        # Load into memory
        memory_manager.load_skill_into_memory(skill, skill_content)

        logger.info(f"Loaded skill: {skill}")
        return f"✓ Loaded skill '{skill_metadata.name}' (ID: {skill}). Skill content added to loaded_skills memory block."

    except Exception as e:
        logger.error(f"Failed to load skill {skill}: {e}")
        error = ActionableError(
            error_type=ErrorType.SKILL_LOAD_ERROR,
            message=f"Failed to load skill '{skill}': {e}",
            suggestions=[
                "Check if the skill file exists and is readable",
                "Verify the skill has valid markdown format",
                "Check file permissions on the .skills directory",
            ],
            recovery_commands=[
                "/skills",
                f"ls -la .skills/{skill}.md",
            ],
            context={"skill_id": skill, "error": str(e)},
            severity="error",
        )
        return _format_error_for_tool(error)


@tool
def unload_skill(skill: str) -> str:
    """Unload a skill from loaded_skills memory block.

    Args:
        skill: The skill ID to unload

    Returns:
        Confirmation message
    """
    try:
        from ..agent import KaiAgent
        agent = _get_current_agent_instance()

        if not agent:
            error = ActionableError(
                error_type=ErrorType.AGENT_NOT_FOUND,
                message="No active agent found",
                suggestions=[
                    "Ensure an agent session is active before unloading skills",
                    "Start a new conversation to initialize the agent",
                ],
                recovery_commands=["/help"],
                severity="warning",
            )
            return _format_error_for_tool(error)

        memory_manager = getattr(agent, '_memory_manager', None)
        if not memory_manager:
            error = ActionableError(
                error_type=ErrorType.SKILL_LOAD_ERROR,
                message="Memory management not available",
                suggestions=[
                    "The agent was not initialized with skill support",
                    "Check if skills are enabled in your configuration",
                ],
                recovery_commands=["/skills"],
                severity="warning",
            )
            return _format_error_for_tool(error)

        # Check if skill is loaded
        loaded_block = memory_manager.get_loaded_skills_block()
        loaded_skills = loaded_block.loaded_skills if loaded_block else {}
        loaded_skill_ids = list(loaded_skills.keys())

        if not loaded_block or skill not in loaded_skills:
            # Suggest similar loaded skills if any
            similar = suggest_values(skill, loaded_skill_ids, n=3, cutoff=0.6)
            error = ActionableError(
                error_type=ErrorType.SKILL_NOT_FOUND,
                message=f"Skill '{skill}' is not currently loaded",
                suggestions=[
                    "The skill must be loaded before it can be unloaded",
                    "Check the list of currently loaded skills",
                ],
                recovery_commands=[
                    "/skills",
                    f"/load {skill}",
                ],
                related_items=similar if similar else loaded_skill_ids[:3],
                context={
                    "skill_id": skill,
                    "loaded_count": str(len(loaded_skill_ids)),
                },
                severity="warning",
            )
            return _format_error_for_tool(error)

        # Remove from memory
        success = memory_manager.unload_skill_from_memory(skill)

        if success:
            logger.info(f"Unloaded skill: {skill}")
            return f"✓ Unloaded skill '{skill}'. Skill content removed from loaded_skills memory block."
        else:
            error = ActionableError(
                error_type=ErrorType.SKILL_LOAD_ERROR,
                message=f"Failed to unload skill '{skill}'",
                suggestions=[
                    "An unexpected error occurred while unloading the skill",
                    "Try reloading all skills and attempting again",
                ],
                recovery_commands=[
                    "/skills",
                    "/skill reload",
                ],
                context={"skill_id": skill},
                severity="error",
            )
            return _format_error_for_tool(error)

    except Exception as e:
        logger.error(f"Failed to unload skill {skill}: {e}")
        error = ActionableError(
            error_type=ErrorType.SKILL_LOAD_ERROR,
            message=f"Failed to unload skill '{skill}': {e}",
            suggestions=[
                "An unexpected error occurred during skill unload",
                "Try reloading all skills to reset state",
            ],
            recovery_commands=[
                "/skills",
                "/skill reload",
            ],
            context={"skill_id": skill, "error": str(e)},
            severity="error",
        )
        return _format_error_for_tool(error)


@tool
def list_skills() -> str:
    """List available skills and currently loaded skills.

    Returns:
        Formatted list of skills and their status
    """
    try:
        from ..agent import KaiAgent
        agent = _get_current_agent_instance()

        if not agent:
            error = ActionableError(
                error_type=ErrorType.AGENT_NOT_FOUND,
                message="No active agent found",
                suggestions=[
                    "Ensure an agent session is active before listing skills",
                    "Start a new conversation to initialize the agent",
                ],
                recovery_commands=["/help"],
                severity="warning",
            )
            return _format_error_for_tool(error)

        memory_manager = getattr(agent, '_memory_manager', None)
        skills_dir = getattr(agent, '_config', None)
        skills_directory = skills_dir.skills_dir if skills_dir else ".skills"

        # Get available skills
        from ..skills_parser import discover_skills
        result = discover_skills(agent._config.root_dir, skills_directory)

        # Get loaded skills
        loaded_skills: Dict[str, str] = {}
        if memory_manager:
            loaded_block = memory_manager.get_loaded_skills_block()
            if loaded_block:
                loaded_skills = loaded_block.loaded_skills

        # Format output
        lines = ["Available Skills:"]

        for skill in result.skills:
            status = "✓ LOADED" if skill.skill_id in loaded_skills else "  Available"
            name_line = f"  {skill.name} (ID: {skill.skill_id}) - {status}"
            lines.append(name_line)

            if skill.description:
                desc_line = f"    Description: {skill.description}"
                lines.append(desc_line)

            if skill.tags:
                tags_line = f"    Tags: {', '.join(skill.tags)}"
                lines.append(tags_line)

            lines.append("")  # Add spacing

        if not result.skills:
            error = ActionableError(
                error_type=ErrorType.SKILL_NOT_FOUND,
                message="No skills found in .skills directory",
                suggestions=[
                    "Create a .skills directory in your project root",
                    "Add skill files with .md extension to the .skills directory",
                    "Skills must have valid YAML frontmatter with skill metadata",
                ],
                recovery_commands=[
                    "mkdir -p .skills",
                    "ls -la .skills",
                ],
                context={"skills_directory": skills_directory},
                severity="info",
            )
            return _format_error_for_tool(error)

        return "\n".join(lines)

    except Exception as e:
        logger.error(f"Failed to list skills: {e}")
        error = ActionableError(
            error_type=ErrorType.SKILL_LOAD_ERROR,
            message=f"Failed to list skills: {e}",
            suggestions=[
                "Check if the .skills directory exists and is readable",
                "Verify skill files have valid YAML frontmatter",
            ],
            recovery_commands=[
                "ls -la .skills",
                "/skill reload",
            ],
            context={"error": str(e)},
            severity="error",
        )
        return _format_error_for_tool(error)


@tool
def reload_skills() -> str:
    """Rediscover skills and refresh the skills memory block.

    Returns:
        Confirmation message
    """
    try:
        from ..agent import KaiAgent
        agent = _get_current_agent_instance()

        if not agent:
            error = ActionableError(
                error_type=ErrorType.AGENT_NOT_FOUND,
                message="No active agent found",
                suggestions=[
                    "Ensure an agent session is active before reloading skills",
                    "Start a new conversation to initialize the agent",
                ],
                recovery_commands=["/help"],
                severity="warning",
            )
            return _format_error_for_tool(error)

        memory_manager = getattr(agent, '_memory_manager', None)
        skills_dir = getattr(agent, '_config', None)
        skills_directory = skills_dir.skills_dir if skills_dir else ".skills"

        # Reinitialize skills system
        success = initialize_skills_system(
            agent._config.root_dir,
            skills_directory,
            memory_manager
        )

        if success:
            logger.info("Reloaded skills system")
            return "✓ Skills system reloaded. Skills memory block updated with latest discoveries."
        else:
            error = ActionableError(
                error_type=ErrorType.SKILL_LOAD_ERROR,
                message="Failed to reload skills system",
                suggestions=[
                    "Check if the .skills directory exists",
                    "Verify skill files have valid YAML frontmatter",
                    "Ensure memory management is properly initialized",
                ],
                recovery_commands=[
                    "ls -la .skills",
                    "/skills",
                ],
                context={"skills_directory": skills_directory},
                severity="error",
            )
            return _format_error_for_tool(error)

    except Exception as e:
        logger.error(f"Failed to reload skills: {e}")
        error = ActionableError(
            error_type=ErrorType.SKILL_LOAD_ERROR,
            message=f"Failed to reload skills: {e}",
            suggestions=[
                "An error occurred while rediscovering skills",
                "Check if the .skills directory is accessible",
                "Verify skill files have valid markdown format",
            ],
            recovery_commands=[
                "ls -la .skills",
                "/skills",
            ],
            context={"error": str(e)},
            severity="error",
        )
        return _format_error_for_tool(error)


def _get_current_agent_instance() -> Optional["KaiAgent"]:
    """Get the current agent instance - hack for tool access."""
    # This is a limitation of the current architecture
    # In letta-code, tools have access to agent context
    # Here we need to find a way to access the current agent
    # For now, we'll try to get it from the module global
    # This would need to be properly implemented
    
    # Try to get from a global registry or context
    # This is a placeholder - proper implementation would inject context
    
    import sys
    import inspect
    
    # Look for KaiAgent instances in calling frames
    for frame in inspect.stack():
        if 'self' in frame.frame.f_locals:
            agent_instance = frame.frame.f_locals['self']
            if hasattr(agent_instance, '_config') and hasattr(agent_instance, '_memory_manager'):
                return agent_instance
    
    return None
