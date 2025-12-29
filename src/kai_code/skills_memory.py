"""Memory block management for skills system.

Ported from letta-code memory block system with enhancements.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Any
import re

logger = logging.getLogger(__name__)


@dataclass
class MemoryBlock:
    """Represents a memory block with rich metadata."""
    label: str
    content: str
    description: Optional[str] = None
    limit: Optional[int] = None
    is_persistent: bool = True
    is_shared: bool = False


@dataclass
class SkillsMemoryBlock(MemoryBlock):
    """Memory block specifically for skills metadata."""
    skills_directory: str = ".skills"
    skills: List[Dict[str, Any]] = field(default_factory=list)
    
    def __post_init__(self):
        self.label = "skills"
        self.description = "Available skills with metadata for loading"


@dataclass  
class LoadedSkillsMemoryBlock(MemoryBlock):
    """Memory block for currently loaded skill contents."""
    loaded_skills: Dict[str, str] = field(default_factory=dict)
    
    def __post_init__(self):
        self.label = "loaded_skills"
        self.description = "Currently loaded skill contents"


@dataclass
class ProjectMemoryBlock(MemoryBlock):
    """Memory block for project-specific information."""
    
    def __post_init__(self):
        self.label = "project"
        self.description = "Project context, conventions, and important information"


class MemoryManager:
    """Manages memory blocks for agent context."""
    
    def __init__(self):
        self._blocks: Dict[str, MemoryBlock] = {}
        self._load_default_blocks()
    
    def _load_default_blocks(self):
        """Load default memory blocks."""
        # Add skills memory block
        self.add_block(SkillsMemoryBlock())
        
        # Add loaded skills memory block
        self.add_block(LoadedSkillsMemoryBlock())
        
        # Add project memory block (empty by default)
        self.add_block(ProjectMemoryBlock())
    
    def add_block(self, block: MemoryBlock) -> None:
        """Add a memory block."""
        self._blocks[block.label] = block
        logger.debug(f"Added memory block: {block.label}")
    
    def get_block(self, label: str) -> Optional[MemoryBlock]:
        """Get a memory block by label."""
        return self._blocks.get(label)
    
    def remove_block(self, label: str) -> bool:
        """Remove a memory block by label."""
        if label in self._blocks:
            del self._blocks[label]
            logger.debug(f"Removed memory block: {label}")
            return True
        return False
    
    def list_blocks(self) -> List[MemoryBlock]:
        """List all memory blocks."""
        return list(self._blocks.values())
    
    def update_block_content(self, label: str, content: str) -> bool:
        """Update the content of a memory block."""
        if label in self._blocks:
            # Create new block with updated content
            old_block = self._blocks[label]
            new_block = MemoryBlock(
                label=old_block.label,
                content=content,
                description=old_block.description,
                limit=old_block.limit,
                is_persistent=old_block.is_persistent,
                is_shared=old_block.is_shared
            )
            self._blocks[label] = new_block
            logger.debug(f"Updated memory block content: {label}")
            return True
        return False
    
    def get_skills_block(self) -> Optional[SkillsMemoryBlock]:
        """Get the skills memory block."""
        skills_block = self.get_block("skills")
        if isinstance(skills_block, SkillsMemoryBlock):
            return skills_block
        return None
    
    def get_loaded_skills_block(self) -> Optional[LoadedSkillsMemoryBlock]:
        """Get the loaded skills memory block."""
        loaded_block = self.get_block("loaded_skills")
        if isinstance(loaded_block, LoadedSkillsMemoryBlock):
            return loaded_block
        return None
    
    def format_for_prompt(self) -> str:
        """Format all memory blocks for inclusion in system prompt."""
        blocks_content = []
        
        for block in self.list_blocks():
            block_content = block.content
            
            # Add header for non-empty blocks
            if block_content.strip():
                header = f"# {block.label}"
                if block.description:
                    header += f" - {block.description}"
                block_content = f"{header}\n\n{block.content}"
            
            blocks_content.append(block_content)
        
        return "\n\n".join(blocks_content)


def parse_mdx_frontmatter(content: str) -> tuple[Dict[str, str], str]:
    """Parse MDX frontmatter similar to letta-code implementation."""
    frontmatter_regex = r'^---\n([\s\S]*?)\n---\n([\s\S]*)$'
    match = re.match(frontmatter_regex, content, re.MULTILINE | re.DOTALL)
    
    if not match or not match.group(1) or not match.group(2):
        return {}, content
    
    frontmatter_text = match.group(1)
    body = match.group(2).strip()
    frontmatter: Dict[str, str] = {}
    
    # Parse YAML-like frontmatter (simple key: value pairs)
    for line in frontmatter_text.split('\n'):
        colon_index = line.find(':')
        if colon_index > 0:
            key = line[:colon_index].strip()
            value = line[colon_index + 1:].strip()
            frontmatter[key] = value
    
    return frontmatter, body


def create_default_skills_block(skills_directory: str = ".skills") -> SkillsMemoryBlock:
    """Create a default skills memory block."""
    return SkillsMemoryBlock(skills_directory=skills_directory)


def create_empty_loaded_skills_block() -> LoadedSkillsMemoryBlock:
    """Create an empty loaded skills memory block."""
    content = "[CURRENTLY EMPTY]"
    return LoadedSkillsMemoryBlock(content=content)
