"""Smart content selector for compaction.

Determines which messages to keep verbatim vs summarize based on:
- Recency (recent window always kept)
- Importance scoring
- Special tags ([keep])
- Error messages (always kept)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence


@dataclass
class Message:
    """Simplified message for selection.

    In production, this will be the actual Message type from conversation manager.
    """
    role: str
    content: str
    turn: int
    token_count: int = 0
    tool_name: str | None = None
    was_error: bool = False


class SmartContentSelector:
    """Selects which content to keep vs summarize during compaction."""

    def __init__(self, recent_window_turns: int = 10):
        """Initialize selector.

        Args:
            recent_window_turns: Number of recent conversation turns to always keep
        """
        self.recent_window_turns = recent_window_turns

    def classify_messages(
        self,
        messages: Sequence[Message],
    ) -> tuple[list[Message], list[Message]]:
        """Classify messages into keep and summarize piles.

        Args:
            messages: All messages to classify

        Returns:
            (keep_messages, summarize_messages)
        """
        keep = []
        summarize = []

        # Calculate recent window (2 messages per turn: user + assistant)
        if not messages:
            return keep, summarize

        recent_start = max(0, len(messages) - self.recent_window_turns * 2)

        for i, msg in enumerate(messages):
            if self._should_keep(msg, i, recent_start):
                keep.append(msg)
            else:
                summarize.append(msg)

        return keep, summarize

    def _should_keep(self, msg: Message, index: int, recent_start: int) -> bool:
        """Determine if a message should be kept verbatim.

        Args:
            msg: The message to evaluate
            index: Message index in the full list
            recent_start: Index where recent window begins

        Returns:
            True if message should be kept, False if it should be summarized
        """
        # Always keep recent messages
        if index >= recent_start:
            return True

        # Always keep [keep] tagged messages
        if "[keep]" in msg.content.lower():
            return True

        # Always keep error messages
        if msg.role == "tool" and msg.was_error:
            return True

        # Summarize large tool outputs
        if msg.role == "tool" and msg.token_count > 1000:
            return False

        # Use importance score for rest
        return self._calculate_importance_score(msg) > 0.5

    def _calculate_importance_score(self, msg: Message) -> float:
        """Score message by retention importance.

        Args:
            msg: Message to score

        Returns:
            Float from 0.0 (low importance) to 1.0 (high importance)
        """
        score = 0.5  # Base score

        # User questions are important
        if msg.role == "user" and "?" in msg.content:
            score += 0.2

        # Code blocks should be preserved
        if "```" in msg.content:
            score += 0.15

        # Tool calls with errors are critical
        if msg.role == "tool" and msg.was_error:
            score += 0.3

        # Large file reads can be summarized
        if msg.tool_name == "read_file" and msg.token_count > 500:
            score -= 0.2

        # Clamp to [0, 1]
        return min(max(score, 0.0), 1.0)
