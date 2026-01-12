"""Memory block dataclasses.

Ported from letta-code memory block system.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class MemoryBlock:
    """Represents a memory block with rich metadata."""
    label: str
    content: str
    description: str | None = None
    limit: int | None = None
    is_persistent: bool = True
    is_shared: bool = False


@dataclass
class SkillsMemoryBlock(MemoryBlock):
    """Memory block specifically for skills metadata."""
    skills_directory: str = ".skills"
    skills: list[dict[str, Any]] = field(default_factory=list)

    def __post_init__(self):
        if not hasattr(self, 'label'):
            self.label = "skills"
        if not hasattr(self, 'description'):
            self.description = "Available skills with metadata for loading"


@dataclass
class LoadedSkillsMemoryBlock(MemoryBlock):
    """Memory block for currently loaded skill contents."""
    loaded_skills: dict[str, str] = field(default_factory=dict)

    def __post_init__(self):
        if not hasattr(self, 'label'):
            self.label = "loaded_skills"
        if not hasattr(self, 'description'):
            self.description = "Currently loaded skill contents"


@dataclass
class ProjectMemoryBlock(MemoryBlock):
    """Memory block for project-specific information."""
    
    def __post_init__(self):
        if not hasattr(self, 'label'):
            self.label = "project"
        if not hasattr(self, 'description'):
            self.description = "Project context, conventions, and important information"


@dataclass
class PersonaMemoryBlock(MemoryBlock):
    """Memory block for learned behavioral adaptations."""
    
    def __post_init__(self):
        self.label = "persona"
        self.description = "Learned preferences and behavioral adaptations"


@dataclass
class StyleMemoryBlock(MemoryBlock):
    """Memory block for user coding preferences."""
    
    def __post_init__(self):
        self.label = "style"
        self.description = "Coding preferences and communication style"


@dataclass
class HumanMemoryBlock(MemoryBlock):
    """Memory block for human user information."""

    def __post_init__(self):
        self.label = "human"
        self.description = "User information and preferences"


@dataclass
class ConversationHistoryEntry:
    """Represents a single entry in the conversation history.

    Used to store summarized versions of conversation messages
    for long-term context retention.
    """
    timestamp: str
    role: str  # "user" or "assistant"
    summary: str
    message_id: str | None = None


@dataclass
class ConversationHistoryMemoryBlock(MemoryBlock):
    """Memory block for storing summarized conversation history.

    Maintains a list of recent conversation entries with configurable
    maximum size for long-term context retention.
    """
    max_entries: int = 50
    entries: list[ConversationHistoryEntry] = field(default_factory=list)

    def __post_init__(self):
        if not hasattr(self, 'label'):
            self.label = "conversation_history"
        if not hasattr(self, 'description'):
            self.description = "Summarized recent conversation history for context retention"
