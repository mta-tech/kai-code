"""Integration tests for ConversationManager compaction."""

import pytest
from unittest.mock import Mock
from kai_code.rich_ui.conversation_manager import StreamingConversationManager
from kai_code.agent import KaiAgent


@pytest.fixture
def manager():
    """Create a conversation manager for testing."""
    # Mock agent - we only need basic structure
    agent = Mock(spec=KaiAgent)
    return StreamingConversationManager(agent=agent)


def test_get_messages_for_compaction(manager):
    """Can retrieve messages for compaction."""
    manager.state.messages = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi"},
    ]

    messages = manager.get_messages_for_compaction()

    assert len(messages) == 2
    # Should be a copy
    assert messages is not manager.state.messages


def test_rebuild_with_compacted_history(manager):
    """Conversation is rebuilt with summaries."""
    kept = [
        {"role": "user", "content": "Recent message"},
    ]
    summaries = ["[COMPACTED] Earlier conversation summary"]

    manager.rebuild_with_compacted_history(kept, summaries)

    messages = manager.state.messages
    assert len(messages) == 2

    # First message should be the summary
    assert messages[0]["role"] == "system"
    assert "[COMPACTED]" in messages[0]["content"]
    assert messages[0]["metadata"]["compacted"] is True

    # Second message should be the kept message
    assert messages[1]["role"] == "user"
    assert messages[1]["content"] == "Recent message"


def test_rebuild_clears_existing_messages(manager):
    """Rebuilding clears existing messages first."""
    manager.state.messages = [
        {"role": "user", "content": "Old message 1"},
        {"role": "user", "content": "Old message 2"},
    ]

    manager.rebuild_with_compacted_history([], [])

    assert len(manager.state.messages) == 0
