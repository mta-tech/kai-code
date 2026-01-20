"""Content summarizer for compaction."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from kai_code.compaction.prompts import build_summarization_prompt

if TYPE_CHECKING:
    from langchain_core.language_models import BaseLLM


logger = logging.getLogger("kai_code.compaction")


class ContentSummarizer:
    """Generates summaries of conversation content using LLM."""

    def __init__(self, max_summary_tokens: int = 1000):
        """Initialize summarizer.

        Args:
            max_summary_tokens: Target maximum size for each summary
        """
        self.max_summary_tokens = max_summary_tokens

    async def summarize_batch(
        self,
        messages: list[dict],  # Will be proper Message type in integration
        llm: BaseLLM,
    ) -> str:
        """Summarize a batch of messages.

        Args:
            messages: List of messages to summarize
            llm: Language model to use for summarization

        Returns:
            Summarized content as a string
        """
        # Format messages for the prompt
        formatted = self._format_messages(messages)
        prompt = build_summarization_prompt(formatted)

        try:
            response = await llm.ainvoke(prompt)
            summary = response.content
            logger.info(f"Generated summary: {len(summary)} chars")
            return summary

        except Exception as e:
            logger.error(f"Summarization failed: {e}")
            raise

    def _format_messages(self, messages: list[dict]) -> list[str]:
        """Format messages for the summarization prompt.

        Args:
            messages: Raw message dictionaries

        Returns:
            List of formatted message strings
        """
        formatted = []
        for msg in messages:
            role = msg.get("role", "unknown").upper()
            content = msg.get("content", "")

            # Truncate very long messages
            if len(content) > 500:
                content = content[:500] + "..."

            formatted.append(f"{role}: {content}")

        return formatted
