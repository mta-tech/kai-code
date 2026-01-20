"""Integration tests for full compaction flow."""

import pytest
from unittest.mock import AsyncMock, Mock
from kai_code.compaction.manager import CompactionManager
from kai_code.compaction.selector import Message


@pytest.mark.asyncio
async def test_full_compaction_flow():
    """Test complete compaction from trigger to summary generation."""
    manager = CompactionManager(threshold=0.85, recent_window_turns=5)

    # Mock LLM
    mock_llm = AsyncMock()
    mock_response = Mock()
    mock_response.content = "[COMPACTED] Summary"
    mock_llm.ainvoke.return_value = mock_response

    # Create test messages as dicts (15 = 7.5 turns, recent window of 5 turns = 10 messages)
    messages = [
        {"role": "user", "content": f"Message {i}", "turn": i // 2, "token_count": 100}
        for i in range(15)
    ]

    # Trigger compaction
    result = await manager.check_and_compact(0.90, messages, mock_llm)

    assert result is True
    assert manager.state.name == "COMPLETE"
    assert manager.last_compaction_time is not None


@pytest.mark.asyncio
async def test_compaction_handles_summarization_failure():
    """Compaction fails gracefully when LLM fails."""
    manager = CompactionManager(recent_window_turns=5)

    # Mock LLM that fails
    mock_llm = AsyncMock()
    mock_llm.ainvoke.side_effect = Exception("API error")

    # Create enough messages to have some outside recent window
    # 15 messages = 7.5 turns, recent window 5 turns = 10 messages
    # So 5 messages should be summarized (and trigger the LLM failure)
    messages = [
        {"role": "user", "content": f"Message {i}", "turn": i // 2, "token_count": 100}
        for i in range(15)
    ]

    result = await manager.check_and_compact(0.90, messages, mock_llm)

    assert result is False  # Compaction failed
    assert manager.state.name == "FAILED"


@pytest.mark.asyncio
async def test_compaction_without_llm_returns_false():
    """Compaction returns False when LLM not provided."""
    manager = CompactionManager()

    result = await manager.check_and_compact(
        0.90,
        [{"role": "user", "content": "test", "turn": 0, "token_count": 100}],
        None
    )

    assert result is False
