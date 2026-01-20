"""Compaction manager - orchestrates the auto-compact process."""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING

from kai_code.compaction.selector import SmartContentSelector
from kai_code.compaction.state import CompactionState
from kai_code.compaction.summarizer import ContentSummarizer

if TYPE_CHECKING:
    from collections.abc import Sequence


logger = logging.getLogger("kai_code.compaction")


class CompactionManager:
    """Coordinates the auto-compaction process.

    Lifecycle:
    1. TokenTracker detects 85% usage
    2. check_and_compact() is called
    3. Messages are classified by SmartContentSelector
    4. ContentSummarizer generates summaries (Phase 2)
    5. ConversationManager rebuilds history (Phase 2)
    """

    def __init__(
        self,
        threshold: float = 0.85,
        recent_window_turns: int = 10,
        min_time_between: int = 300,
    ):
        """Initialize compaction manager.

        Args:
            threshold: Context usage percentage (0.0-1.0) to trigger compaction
            recent_window_turns: Number of recent turns to always keep verbatim
            min_time_between: Minimum seconds between compactions
        """
        self.threshold = threshold
        self.recent_window_turns = recent_window_turns
        self.min_time_between = min_time_between

        # State tracking
        self.state: CompactionState = CompactionState.IDLE
        self.last_compaction_time: float | None = None

        # Components (selector now, summarizer in Phase 2)
        self.selector = SmartContentSelector(recent_window_turns)
        # self.summarizer = ContentSummarizer()  # Phase 2

    async def check_and_compact(
        self,
        usage_percentage: float,
        conversation_messages: list[dict] | None = None,
        llm = None,  # LangChain LLM
    ) -> bool:
        """Check threshold and trigger compaction if needed.

        Args:
            usage_percentage: Current context usage (0.0-1.0)
            conversation_messages: List of conversation messages to compact
            llm: Language model for summarization

        Returns:
            True if compaction was triggered, False otherwise
        """
        if not self._should_compact(usage_percentage):
            return False

        # Phase 1: Skeleton only returned True here
        # Phase 2: Full compaction flow
        if conversation_messages is None or llm is None:
            # Can't compact without messages or LLM
            logger.warning("Compaction triggered but no messages/LLM available")
            return False

        self.state = CompactionState.COMPACTING
        logger.info(
            f"Compaction triggered at {usage_percentage:.1%} usage "
            f"({len(conversation_messages)} messages)"
        )

        try:
            # Convert dicts to Message objects for selector
            from kai_code.compaction.selector import Message
            message_objects = [
                Message(
                    role=msg.get("role", "user"),
                    content=msg.get("content", ""),
                    turn=msg.get("turn", 0),
                    token_count=msg.get("token_count", 0),
                    tool_name=msg.get("tool_name"),
                    was_error=msg.get("was_error", False),
                )
                for msg in conversation_messages
            ]

            # Classify messages
            keep, summarize = self.selector.classify_messages(message_objects)

            logger.info(f"Keeping {len(keep)} messages, summarizing {len(summarize)}")

            # Summarize in batches
            summarizer = ContentSummarizer()
            summaries = []

            # Convert Message objects to dicts for summarizer
            summarize_dicts = [
                {
                    "role": msg.role,
                    "content": msg.content,
                    "turn": msg.turn,
                    "token_count": msg.token_count,
                }
                for msg in summarize
            ]

            # Process in batches of 10 messages
            batch_size = 10
            for i in range(0, len(summarize_dicts), batch_size):
                batch = summarize_dicts[i:i + batch_size]
                summary = await summarizer.summarize_batch(batch, llm)
                summaries.append(summary)

            self.state = CompactionState.REBUILDING
            logger.info(f"Generated {len(summaries)} summaries")

            # In full implementation, would rebuild conversation here
            # For now, just mark complete
            self.state = CompactionState.COMPLETE
            self.last_compaction_time = time.time()

            logger.info("Compaction complete")
            return True

        except Exception as e:
            self.state = CompactionState.FAILED
            logger.error(f"Compaction failed: {e}")
            return False

    def is_running(self) -> bool:
        """Check if compaction is currently in progress.

        Returns:
            True if in TRIGGERED, COMPACTING, or REBUILDING state
        """
        return self.state in (
            CompactionState.TRIGGERED,
            CompactionState.COMPACTING,
            CompactionState.REBUILDING,
        )

    def _should_compact(self, usage_percentage: float) -> bool:
        """Check if compaction should trigger.

        Args:
            usage_percentage: Current context usage (0.0-1.0)

        Returns:
            True if compaction should run
        """
        # Check threshold
        if usage_percentage < self.threshold:
            return False

        # Check cooldown
        if self.last_compaction_time:
            elapsed = time.time() - self.last_compaction_time
            if elapsed < self.min_time_between:
                logger.debug(
                    f"Compaction cooldown active: {elapsed:.0f}s < {self.min_time_between}s"
                )
                return False

        # Check already running
        if self.is_running():
            logger.debug("Compaction already in progress")
            return False

        return True
