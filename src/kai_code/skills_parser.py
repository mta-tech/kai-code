"""Advanced skills parsing and discovery system.

Ported from letta-code TypeScript implementation with enhancements.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Dict, Any


@dataclass(frozen=True)
class SkillMetadata:
    """Rich metadata for a discovered skill."""
    skill_id: str
    name: str
    description: str
    path: Path
    category: Optional[str] = None
    tags: List[str] = None
    license: Optional[str] = None
    frontmatter: Dict[str, Any] = None


@dataclass(frozen=True)
class SkillDiscoveryResult:
    """Result of skill discovery operation."""
    skills: List[SkillMetadata]
    errors: List[str]


def parse_frontmatter(content: str) -> tuple[Dict[str, Any], str]:
    """Parse YAML-like frontmatter from markdown content.
    
    Supports simple key: value pairs and arrays similar to letta-code implementation.
    """
    frontmatter_regex = r'^---\n([\s\S]*?)\n---\n([\s\S]*)$'
    match = re.match(frontmatter_regex, content, re.MULTILINE | re.DOTALL)
    
    if not match or not match.group(1) or not match.group(2):
        return {}, content
    
    frontmatter_text = match.group(1)
    body = match.group(2).strip()
    frontmatter: Dict[str, Any] = {}
    
    # Parse YAML-like frontmatter
    lines = frontmatter_text.split('\n')
    current_key: Optional[str] = None
    current_array: List[str] = []
    
    for line in lines:
        line = line.strip()
        
        # Check if this is an array item
        if line.startswith('-') and current_key:
            value = line[1:].strip()
            current_array.append(value)
            continue
        
        # If we were building an array, save it
        if current_key and current_array:
            frontmatter[current_key] = current_array.copy()
            current_key = None
            current_array = []
        
        # Parse key: value pair
        colon_index = line.find(':')
        if colon_index > 0:
            key = line[:colon_index].strip()
            value = line[colon_index + 1:].strip()
            current_key = key
            
            if value:
                # Simple key: value pair
                frontmatter[key] = value
                current_key = None
            else:
                # Might be starting an array
                current_array = []
    
    # Save any remaining array
    if current_key and current_array:
        frontmatter[current_key] = current_array
    
    return frontmatter, body


def parse_skill_metadata(file_path: Path, root_path: Path) -> SkillMetadata:
    """Parse skill metadata from SKILL.MD file.
    
    Args:
        file_path: Path to SKILL.MD file
        root_path: Root skills directory for resolving relative paths
        
    Returns:
        SkillMetadata object
        
    Raises:
        ValueError: If required fields are missing
    """
    if not file_path.exists():
        raise ValueError(f"Skill file not found: {file_path}")
    
    content = file_path.read_text(encoding='utf-8')
    frontmatter, body = parse_frontmatter(content)
    
    # Derive ID from directory structure relative to root
    # E.g., .skills/data-analysis/SKILL.MD -> "data-analysis"
    normalized_root = str(root_path).rstrip('/')
    relative_path = str(file_path)[len(normalized_root) + 1:]  # +1 to remove leading slash
    dir_path = relative_path[:-len('/SKILL.MD')]
    default_id = dir_path or "root"
    
    # Use ID from frontmatter or derive from path
    skill_id = frontmatter.get('id', default_id)
    
    # Use name from frontmatter with fallbacks
    name = (
        frontmatter.get('name') or 
        frontmatter.get('title') or
        (skill_id.split('/')[-1].replace('-', ' ').title() if skill_id else "")
    )
    
    # Description is required - extract from frontmatter or first paragraph
    description = frontmatter.get('description')
    if not description:
        # Extract first paragraph from body
        first_paragraph = body.strip().split('\n\n')[0]
        description = first_paragraph or "No description available"
    
    # Strip surrounding quotes from description if present
    description = description.strip()
    if (
        (description.startswith('"') and description.endswith('"')) or
        (description.startswith("'") and description.endswith("'"))
    ):
        description = description[1:-1]
    
    # Handle tags (both string and array)
    tags = frontmatter.get('tags')
    if isinstance(tags, str):
        tags = [tags]
    elif isinstance(tags, list):
        tags = tags
    else:
        tags = []
    
    return SkillMetadata(
        skill_id=skill_id,
        name=name,
        description=description,
        category=frontmatter.get('category'),
        tags=tags,
        path=file_path,
        license=frontmatter.get('license'),
        frontmatter=frontmatter
    )


def discover_skills(
    skills_path: str | Path = ".skills",
    root_dir: Optional[Path] = None
) -> SkillDiscoveryResult:
    """Discover skills by recursively searching for SKILL.MD files.
    
    Args:
        skills_path: Directory to search for skills (default: .skills)
        root_dir: Root project directory (defaults to skills_path parent)
        
    Returns:
        SkillDiscoveryResult with discovered skills and any errors
    """
    skills_path = Path(skills_path)
    if root_dir is None:
        root_dir = skills_path.parent.resolve()
    else:
        root_dir = Path(root_dir).resolve()
    
    errors: List[str] = []
    skills: List[SkillMetadata] = []
    
    # Check if skills directory exists
    if not skills_path.exists() or not skills_path.is_dir():
        return SkillDiscoveryResult(skills=[], errors=[])
    
    try:
        # Recursively find all SKILL.MD files (case-insensitive)
        skill_files = list(skills_path.rglob("SKILL.MD"))
        skill_files.extend(skills_path.rglob("skill.md"))  # Also check lowercase
        
        for file_path in skill_files:
            try:
                skill = parse_skill_metadata(file_path, skills_path)
                skills.append(skill)
            except Exception as e:
                errors.append(f"Failed to parse {file_path}: {e}")
        
        # Sort skills by ID and then by name
        skills.sort(key=lambda s: (s.skill_id.lower(), s.name.lower()))
        
    except Exception as e:
        errors.append(f"Failed to read skills directory {skills_path}: {e}")
    
    return SkillDiscoveryResult(skills=skills, errors=errors)


def format_skills_for_prompt(
    skills: List[SkillMetadata],
    skills_directory: str | Path = ".skills"
) -> str:
    """Format discovered skills as a string for skills memory block.
    
    Similar to letta-code implementation with categories and rich formatting.
    
    Args:
        skills: List of discovered skill metadata
        skills_directory: Skills directory path for display
        
    Returns:
        Formatted string for memory block
    """
    if not skills:
        return f"Skills Directory: {skills_directory}\n\n[NO SKILLS AVAILABLE]"
    
    lines = [f"Skills Directory: {skills_directory}\n"]
    
    # Group skills by category if categories exist
    categorized: Dict[str, List[SkillMetadata]] = {}
    uncategorized: List[SkillMetadata] = []
    
    for skill in skills:
        if skill.category:
            if skill.category not in categorized:
                categorized[skill.category] = []
            categorized[skill.category].append(skill)
        else:
            uncategorized.append(skill)
    
    # Output categorized skills
    for category, category_skills in categorized.items():
        lines.append(f"\n## {category}\n")
        for skill in category_skills:
            lines.append(_format_skill_for_prompt(skill))
        lines.append("")
    
    # Output uncategorized skills
    if uncategorized:
        if categorized:  # Only show "Other" if we have categories
            lines.append("\n## Other\n")
        for skill in uncategorized:
            lines.append(_format_skill_for_prompt(skill))
        lines.append("")
    
    return "\n".join(lines).strip()


def _format_skill_for_prompt(skill: SkillMetadata) -> str:
    """Format a single skill for the skills memory block."""
    lines = [
        f"### {skill.name}",
        f"ID: `{skill.skill_id}`",
        f"Description: {skill.description}"
    ]
    
    if skill.tags:
        tags_formatted = ", ".join(f"`{tag}`" for tag in skill.tags)
        lines.append(f"Tags: {tags_formatted}")
    
    lines.append("")  # Add spacing between skills
    return "\n".join(lines)


def validate_skill_metadata(skill: SkillMetadata) -> List[str]:
    """Validate skill metadata and return list of issues.
    
    Args:
        skill: Skill metadata to validate
        
    Returns:
        List of validation issues (empty if valid)
    """
    issues: List[str] = []
    
    # Required fields
    if not skill.skill_id.strip():
        issues.append("Skill ID is required")
    if not skill.name.strip():
        issues.append("Skill name is required")
    if not skill.description.strip():
        issues.append("Skill description is required")
    
    # Path validation
    if not skill.path.exists():
        issues.append(f"Skill file not found: {skill.path}")
    
    # ID format validation
    if not re.match(r'^[a-zA-Z0-9_-]+$', skill.skill_id):
        issues.append(f"Invalid skill ID format: {skill.skill_id}. Use alphanumeric, underscore, and hyphen only")
    
    return issues


# Default skills directory constant (matches letta-code)
SKILLS_DIR = ".skills"
