"""Tests for ContentSummarizer."""

import pytest
from unittest.mock import AsyncMock, Mock
from kai_code.compaction.summarizer import ContentSummarizer


@pytest.mark.asyncio
async def test_summarizer_calls_llm():
    """Summarizer invokes LLM with proper prompt."""
    summarizer = ContentSummarizer()

    # Mock LLM response
    mock_llm = AsyncMock()
    mock_response = Mock()
    mock_response.content = "[COMPACTED] Summary of conversation"
    mock_llm.ainvoke.return_value = mock_response

    messages = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there!"},
    ]

    result = await summarizer.summarize_batch(messages, mock_llm)

    assert "[COMPACTED]" in result
    mock_llm.ainvoke.assert_called_once()


@pytest.mark.asyncio
async def test_summarizer_handles_llm_error():
    """Summarizer propagates LLM errors."""
    summarizer = ContentSummarizer()

    mock_llm = AsyncMock()
    mock_llm.ainvoke.side_effect = Exception("API error")

    messages = [{"role": "user", "content": "test"}]

    with pytest.raises(Exception, match="API error"):
        await summarizer.summarize_batch(messages, mock_llm)


def test_format_messages():
    """Messages are formatted correctly for prompt."""
    summarizer = ContentSummarizer()

    messages = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi!"},
    ]

    result = summarizer._format_messages(messages)

    assert len(result) == 2
    assert "USER: Hello" in result[0]
    assert "ASSISTANT: Hi!" in result[1]


def test_format_messages_truncates_long_content():
    """Long messages are truncated in formatted output."""
    summarizer = ContentSummarizer()

    messages = [
        {"role": "user", "content": "x" * 1000}  # Very long
    ]

    result = summarizer._format_messages(messages)

    assert len(result[0]) < 600  # "USER: " + 500 chars + "..."
    assert "..." in result[0]
