"""Memory block manager implementation.

Ported from letta-code memory management system.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path

from .blocks import (
    MemoryBlock,
    SkillsMemoryBlock,
    LoadedSkillsMemoryBlock,
    ProjectMemoryBlock,
    ConversationHistoryMemoryBlock,
    ConversationHistoryEntry,
)
from ..skills_parser import SkillMetadata, format_skills_for_prompt
from ..skills_memory import parse_mdx_frontmatter

logger = logging.getLogger(__name__)


class MemoryManager:
    """Manages memory blocks for agent context."""
    
    def __init__(self, root_dir: Optional[Path] = None):
        self._blocks: Dict[str, MemoryBlock] = {}
        self._root_dir = root_dir or Path.cwd()
        self._skills_block: Optional[SkillsMemoryBlock] = None
        self._loaded_skills_block: Optional[LoadedSkillsMemoryBlock] = None
        self._project_block: Optional[ProjectMemoryBlock] = None
        self._history_block: Optional[ConversationHistoryMemoryBlock] = None
        self._load_default_blocks()
    
    def _load_default_blocks(self):
        """Load default memory blocks."""
        # Add skills memory block
        self._skills_block = SkillsMemoryBlock(
            label="skills",
            content="[CURRENTLY EMPTY]",
            description="Available skills with metadata for loading",
            skills_directory=".skills"
        )
        self.add_block(self._skills_block)
        
        # Add loaded skills memory block  
        self._loaded_skills_block = LoadedSkillsMemoryBlock(
            label="loaded_skills",
            content="[CURRENTLY EMPTY]",
            description="Currently loaded skill contents"
        )
        self.add_block(self._loaded_skills_block)
        
        # Add project memory block (empty by default)
        self._project_block = ProjectMemoryBlock(
            label="project",
            content="[CURRENTLY EMPTY]",
            description="Project context, conventions, and important information"
        )
        self.add_block(self._project_block)

        # Add conversation history memory block
        self._history_block = ConversationHistoryMemoryBlock(
            label="conversation_history",
            content="[CURRENTLY EMPTY]",
            description="Summarized recent conversation history for context retention"
        )
        self.add_block(self._history_block)

        logger.debug("Loaded default memory blocks: skills, loaded_skills, project, conversation_history")
    
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
    
    def get_skills_block(self) -> Optional[SkillsMemoryBlock]:
        """Get skills memory block."""
        return self._skills_block
    
    def get_loaded_skills_block(self) -> Optional[LoadedSkillsMemoryBlock]:
        """Get loaded skills memory block."""
        return self._loaded_skills_block

    def get_history_block(self) -> Optional[ConversationHistoryMemoryBlock]:
        """Get conversation history memory block."""
        return self._history_block

    def add_history_entry(
        self,
        role: str,
        summary: str,
        message_id: Optional[str] = None
    ) -> None:
        """Add a new entry to the conversation history.

        Creates a ConversationHistoryEntry with current timestamp and appends it to
        the history block. Automatically removes oldest entries when max_entries is exceeded.

        Args:
            role: The role of the message sender ("user" or "assistant")
            summary: Condensed version of the message content
            message_id: Optional reference ID for the original message
        """
        if self._history_block:
            # Create new entry with current timestamp
            entry = ConversationHistoryEntry(
                timestamp=datetime.now().isoformat(),
                role=role,
                summary=summary,
                message_id=message_id
            )

            # Add entry to history
            self._history_block.entries.append(entry)

            # Enforce max_entries limit by removing oldest entries
            while len(self._history_block.entries) > self._history_block.max_entries:
                self._history_block.entries.pop(0)

            # Update the block content to reflect current history
            self._update_history_content()

            logger.debug(f"Added history entry: {role} - {summary[:50]}...")
        else:
            logger.error("History block not initialized")

    def get_skill_blocks(self) -> tuple[Optional[SkillsMemoryBlock], Optional[LoadedSkillsMemoryBlock]]:
        """Get skills-related memory blocks."""
        skills_block = self.get_skills_block()
        loaded_block = self.get_loaded_skills_block()
        return skills_block, loaded_block
    
    def update_block_content(self, label: str, content: str, description: Optional[str] = None) -> bool:
        """Update content of a memory block."""
        if label in self._blocks:
            old_block = self._blocks[label]
            new_block = MemoryBlock(
                label=old_block.label,
                content=content,
                description=description or old_block.description,
                limit=old_block.limit,
                is_persistent=old_block.is_persistent,
                is_shared=old_block.is_shared
            )
            self._blocks[label] = new_block
            logger.debug(f"Updated memory block content: {label}")
            return True
        return False
    
    def update_skills_discovery(self, skills: List[SkillMetadata], skills_directory: str = ".skills") -> None:
        """Update skills memory block with discovered skills."""
        from ..skills_parser import format_skills_for_prompt
        
        skills_block = self.get_block("skills")
        if isinstance(skills_block, SkillsMemoryBlock):
            # Update skills directory
            skills_block.skills_directory = skills_directory
            
            # Format skills content
            skills_content = format_skills_for_prompt(skills, skills_directory=skills_directory)
            self.update_block_content("skills", skills_content)
            
            logger.debug(f"Updated skills memory block with {len(skills)} skills")
    
    def load_skill_into_memory(self, skill_id: str, skill_content: str) -> None:
        """Load a skill into the loaded_skills memory block."""
        if self._loaded_skills_block:
            self._loaded_skills_block.loaded_skills[skill_id] = skill_content
            # Update the memory block content to reflect loaded skills
            self._update_loaded_skills_content(self._loaded_skills_block)
            logger.debug(f"Loaded skill into memory: {skill_id}")
        else:
            logger.error(f"Loaded skills block not initialized")
    
    def unload_skill_from_memory(self, skill_id: str) -> bool:
        """Unload a skill from the loaded_skills memory block.""" 
        if self._loaded_skills_block and skill_id in self._loaded_skills_block.loaded_skills:
            del self._loaded_skills_block.loaded_skills[skill_id]
            self._update_loaded_skills_content(self._loaded_skills_block)
            logger.debug(f"Unloaded skill from memory: {skill_id}")
            return True
        return False
    
    def _update_loaded_skills_content(self, loaded_block: LoadedSkillsMemoryBlock) -> None:
        """Update the content of loaded_skills block to reflect current loaded skills."""
        if not loaded_block.loaded_skills:
            content = "[CURRENTLY EMPTY]"
        else:
            lines = ["[CURRENTLY LOADED SKILLS]"]
            for skill_id, skill_content in loaded_block.loaded_skills.items():
                lines.append(f"\n# Skill: {skill_id}")
                lines.append(skill_content)
            content = "\n".join(lines)
        
        self.update_block_content("loaded_skills", content)

    def _update_history_content(self) -> None:
        """Update the content of conversation_history block to reflect current entries.

        Formats history entries as a chronological, readable string for inclusion
        in prompts. Each entry shows timestamp, role, and summary.
        """
        if not self._history_block:
            return

        if not self._history_block.entries:
            content = "[CURRENTLY EMPTY]"
        else:
            lines = ["[CONVERSATION HISTORY]"]
            lines.append("")
            for entry in self._history_block.entries:
                # Format: [timestamp] role: summary
                role_display = entry.role.capitalize()
                lines.append(f"[{entry.timestamp}] {role_display}: {entry.summary}")
            content = "\n".join(lines)

        self.update_block_content("conversation_history", content)

    def list_loaded_skills(self) -> Dict[str, str]:
        """Get dictionary of currently loaded skills."""
        if self._loaded_skills_block:
            return self._loaded_skills_block.loaded_skills.copy()
        return {}
    
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


def load_memory_blocks_from_directory(
    blocks_dir: str | Path,
    root_dir: Optional[Path] = None
) -> List[MemoryBlock]:
    """Load memory blocks from MDX files in a directory.
    
    Similar to letta-code's loadMemoryBlocksFromMdx function.
    """
    blocks_dir = Path(blocks_dir)
    if not blocks_dir.exists():
        logger.warning(f"Memory blocks directory not found: {blocks_dir}")
        return []
    
    # Look for .mdx and .md files
    block_files = (
        list(blocks_dir.glob("*.mdx")) +
        list(blocks_dir.glob("*.md"))
    )
    
    blocks: List[MemoryBlock] = []
    for file_path in block_files:
        try:
            content = file_path.read_text(encoding='utf-8')
            frontmatter, body = parse_mdx_frontmatter(content)
            
            label = frontmatter.get('label', file_path.stem)
            description = frontmatter.get('description')
            
            block = MemoryBlock(
                label=label,
                content=body.strip(),
                description=description
            )
            
            blocks.append(block)
            logger.debug(f"Loaded memory block: {label} from {file_path}")
            
        except Exception as e:
            logger.error(f"Failed to load memory block {file_path}: {e}")
    
    return blocks
