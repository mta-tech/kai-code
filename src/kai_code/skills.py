from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import List

from .skills_parser import SkillMetadata, SkillDiscoveryResult, discover_skills, format_skills_for_prompt
# Import memory components conditionally to avoid circular import
MemoryManager = None
def get_memory_manager():
    global MemoryManager
    if MemoryManager is None:
        from .skills_memory import MemoryManager
    return MemoryManager

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Skill:
    """Legacy basic skill for backward compatibility."""
    skill_id: str
    path: Path


def discover_skills_legacy(root_dir: Path, skills_dir: str = ".skills") -> list[Skill]:
    """Legacy skill discovery for backward compatibility."""
    base = (root_dir / skills_dir).resolve()
    if not base.exists() or not base.is_dir():
        return []
    skills: list[Skill] = []
    for path in base.rglob("SKILL.MD"):
        try:
            rel = path.relative_to(base)
        except ValueError:
            continue
        # skill id = directory path without trailing SKILL.MD
        skill_id = str(rel.parent).replace("\\", "/")
        skills.append(Skill(skill_id=skill_id, path=path))
    skills.sort(key=lambda s: s.skill_id)
    return skills


def discover_skills_enhanced(
    root_dir: Path, 
    skills_dir: str = ".skills",
    memory_manager = None
) -> SkillDiscoveryResult:
    """Enhanced skill discovery with metadata and memory integration."""
    if memory_manager:
        # Update skills memory block
        skills_block = memory_manager.get_skills_block()
        if skills_block:
            skills_block.skills_directory = skills_dir
            
            # Get skills directory path
            skills_path = (root_dir / skills_dir).resolve()
            
            # Discover skills (using direct function to avoid recursion)
            from .skills_parser import discover_skills as direct_discover
            result = direct_discover(skills_path, root_dir)
            
            # Update skills memory block with new discoveries
            from .skills_parser import format_skills_for_prompt as direct_format
            skills_content = direct_format(result.skills, skills_directory=skills_dir)
            memory_manager.update_block_content("skills", skills_content)
            
            logger.debug(f"Updated skills memory block with {len(result.skills)} skills")
            return result
    
    # Fallback to direct discovery
    skills_path = (root_dir / skills_dir).resolve()
    from .skills_parser import discover_skills as direct_discover
    return direct_discover(skills_path, root_dir)


def format_skills_for_prompt_legacy(skills: list[Skill], *, skills_dir: str = ".skills") -> str:
    """Legacy skill formatting for backward compatibility."""
    if not skills:
        return ""
    lines = [
        "Project skills were discovered in ./.skills (read with glob/read_file):",
    ]
    for s in skills:
        # agent will use virtual paths, but we only have real path here; prompt should be generic
        lines.append(f"- {s.skill_id}: {skills_dir}/{s.skill_id}/SKILL.MD")
    return "\n".join(lines)


def initialize_skills_system(
    root_dir: Path,
    skills_dir: str = ".skills",
    memory_manager = None
) -> bool:
    """Initialize the skills system with memory management integration.
    
    Args:
        root_dir: Project root directory
        skills_dir: Skills directory name
        memory_manager: Optional memory manager for integration
        
    Returns:
        True if initialization successful
    """
    try:
        # Discover and format skills
        result = discover_skills_enhanced(root_dir, skills_dir, memory_manager)
        
        if result.errors:
            logger.warning(f"Skill discovery errors: {result.errors}")
        
        logger.info(f"Discovered {len(result.skills)} skills in {skills_dir}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to initialize skills system: {e}")
        return False


def validate_skill_structure(skill_dir: str = ".skills") -> List[str]:
    """Validate skills directory structure and common issues."""
    issues: List[str] = []
    
    skills_path = Path(skill_dir)
    if not skills_path.exists():
        issues.append("Skills directory does not exist")
        return issues
    
    # Check for common issues
    skill_files = list(skills_path.rglob("SKILL.MD"))
    if not skill_files:
        issues.append("No SKILL.MD files found in skills directory")
    
    # Validate each skill file
    for skill_file in skill_files:
        try:
            from .skills_parser import parse_skill_metadata, validate_skill_metadata
            skill_metadata = parse_skill_metadata(skill_file, skills_path)
            validation_issues = validate_skill_metadata(skill_metadata)
            
            if validation_issues:
                issues.append(f"Skill {skill_file.name}: {', '.join(validation_issues)}")
                
        except Exception as e:
            issues.append(f"Error parsing {skill_file.name}: {e}")
    
    return issues


# Backward compatibility aliases
discover_skills = discover_skills_enhanced
format_skills_for_prompt = format_skills_for_prompt


