"""Skill loading tools - dynamic skill management.

Ported from letta-code Skill tool implementation.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, Optional

from langchain_core.tools import tool

from ..skills_parser import parse_skill_metadata
from ..skills import initialize_skills_system

logger = logging.getLogger(__name__)


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
            return "Error: No active agent found"
        
        # Get memory manager and skills directory
        memory_manager = getattr(agent, '_memory_manager', None)
        if not memory_manager:
            return "Error: Memory management not available"
        
        skills_dir = getattr(agent, '_config', None)
        skills_directory = skills_dir.skills_dir if skills_dir else ".skills"
        
        # Discover skills to find the requested skill
        from ..skills_parser import discover_skills
        result = discover_skills(agent._config.root_dir, skills_directory)
        
        # Find the skill by ID
        skill_metadata = None
        for skill in result.skills:
            if skill.skill_id == skill:
                skill_metadata = skill
                break
        
        if not skill_metadata:
            return f"Error: Skill '{skill}' not found. Available skills: {', '.join(s.skill_id for s in result.skills)}"
        
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
        return f"Error loading skill '{skill}': {e}"


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
            return "Error: No active agent found"
        
        memory_manager = getattr(agent, '_memory_manager', None)
        if not memory_manager:
            return "Error: Memory management not available"
        
        # Check if skill is loaded
        loaded_block = memory_manager.get_loaded_skills_block()
        if not loaded_block or skill not in loaded_block.loaded_skills:
            return f"Skill '{skill}' is not currently loaded"
        
        # Remove from memory
        success = memory_manager.unload_skill_from_memory(skill)
        
        if success:
            logger.info(f"Unloaded skill: {skill}")
            return f"✓ Unloaded skill '{skill}'. Skill content removed from loaded_skills memory block."
        else:
            return f"Error: Failed to unload skill '{skill}'"
            
    except Exception as e:
        logger.error(f"Failed to unload skill {skill}: {e}")
        return f"Error unloading skill '{skill}': {e}"


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
            return "Error: No active agent found"
        
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
            lines.append("  No skills found in .skills directory")
        
        return "\n".join(lines)
        
    except Exception as e:
        logger.error(f"Failed to list skills: {e}")
        return f"Error listing skills: {e}"


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
            return "Error: No active agent found"
        
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
            return "✗ Failed to reload skills system"
            
    except Exception as e:
        logger.error(f"Failed to reload skills: {e}")
        return f"Error reloading skills: {e}"


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
