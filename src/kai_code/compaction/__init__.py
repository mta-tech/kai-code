"""Auto-compaction package for managing conversation history size."""

from kai_code.compaction.state import CompactionState
from kai_code.compaction.selector import SmartContentSelector, Message
from kai_code.compaction.manager import CompactionManager
from kai_code.compaction.summarizer import ContentSummarizer

__all__ = [
    "CompactionState",
    "SmartContentSelector",
    "Message",
    "CompactionManager",
    "ContentSummarizer",
]
