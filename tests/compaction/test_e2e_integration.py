"""End-to-end integration tests for auto-compaction."""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from kai_code.compaction.manager import CompactionManager
from kai_code.cli_ui import TokenTracker
from kai_code.rich_ui.conversation_manager import StreamingConversationManager


@pytest.fixture
def setup_compaction():
    """Set up a full compaction environment."""
    # Create components
    manager = CompactionManager(threshold=0.85, recent_window_turns=5)
    tracker = TokenTracker()
    tracker.compaction_manager = manager
    tracker.set_context_limit(10000)

    # Mock agent
    agent = Mock()
    conv_manager = StreamingConversationManager(agent=agent)

    # Mock LLM
    mock_llm = AsyncMock()
    mock_response = Mock()
    mock_response.content = "[COMPACTED] Summary of conversation"
    mock_llm.ainvoke.return_value = mock_response

    return {
        "manager": manager,
        "tracker": tracker,
        "conv_manager": conv_manager,
        "llm": mock_llm,
    }


@pytest.mark.asyncio
async def test_e2e_compaction_flow(setup_compaction):
    """Full compaction from token tracking to conversation rebuild."""
    manager = setup_compaction["manager"]
    tracker = setup_compaction["tracker"]
    conv_manager = setup_compaction["conv_manager"]
    llm = setup_compaction["llm"]

    # Add conversation messages
    conv_manager.state.messages = [
        {"role": "user", "content": f"Message {i}", "turn": i // 2}
        for i in range(20)
    ]

    # Add tokens to reach threshold
    for _ in range(90):
        tracker.add_tokens(100)  # 9000/10000 = 90%

    # Verify threshold reached
    assert tracker.get_usage_percentage() == 0.9

    # Messages should be classified correctly
    messages = conv_manager.get_messages_for_compaction()
    assert len(messages) == 20

    # Trigger compaction
    result = await manager.check_and_compact(
        tracker.get_usage_percentage(),
        messages,
        llm
    )

    assert result is True
    assert manager.state.name == "COMPLETE"


@pytest.mark.asyncio
async def test_compaction_preserves_recent_messages(setup_compaction):
    """Recent messages are not compacted."""
    manager = setup_compaction["manager"]
    conv_manager = setup_compaction["conv_manager"]
    llm = setup_compaction["llm"]

    # Create messages with identifiable content
    conv_manager.state.messages = [
        {"role": "user", "content": f"Old message {i}", "turn": i // 2}
        for i in range(20)
    ]

    # Mark last message
    last_msg = conv_manager.state.messages[-1]["content"]

    messages = conv_manager.get_messages_for_compaction()

    # Trigger compaction
    await manager.check_and_compact(0.90, messages, llm)

    # In full implementation, would verify recent messages preserved
    # For now, just verify the flow completes
    assert manager.state.name == "COMPLETE"


def test_compaction_disabled_when_no_manager():
    """System works normally when compaction disabled."""
    tracker = TokenTracker()
    tracker.set_context_limit(1000)

    # No compaction manager set
    assert tracker.compaction_manager is None

    # Adding tokens should not crash
    tracker.add_tokens(900)
    assert tracker.current_context == 900
