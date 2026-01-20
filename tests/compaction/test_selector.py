"""Tests for SmartContentSelector."""

import pytest
from kai_code.compaction.selector import SmartContentSelector, Message


def create_message(
    role: str = "user",
    content: str = "test",
    turn: int = 0,
    token_count: int = 100,
    tool_name: str | None = None,
    was_error: bool = False,
) -> Message:
    """Helper to create test messages."""
    return Message(
        role=role,
        content=content,
        turn=turn,
        token_count=token_count,
        tool_name=tool_name,
        was_error=was_error,
    )


def test_selector_classifies_recent_messages():
    """Messages within recent window are kept."""
    selector = SmartContentSelector(recent_window_turns=10)

    # Create 25 messages (12.5 turns)
    messages = [create_message(turn=i // 2) for i in range(25)]

    keep, summarize = selector.classify_messages(messages)

    # Last 20 messages (10 turns * 2) should be kept
    assert len(keep) == 20
    assert len(summarize) == 5


def test_selector_respects_keep_tag():
    """Messages with [keep] tag are always retained."""
    selector = SmartContentSelector(recent_window_turns=5)

    messages = [
        create_message(content="old message", turn=1),  # Old, should be summarized
        create_message(content="[keep] remember this", turn=1),  # Tagged, should be kept
        create_message(content="another old", turn=2),  # Old, should be summarized
    ]

    keep, summarize = selector.classify_messages(messages)

    # Recent window of 0 (all messages are "old"), but [keep] is preserved
    assert len(keep) >= 1
    assert any("[keep]" in m.content for m in keep)


def test_selector_keeps_error_messages():
    """Error messages from tools are always kept."""
    selector = SmartContentSelector(recent_window_turns=0)

    messages = [
        create_message(role="tool", content="success", was_error=False),
        create_message(role="tool", content="error occurred", was_error=True),
    ]

    keep, summarize = selector.classify_messages(messages)

    # Error message should be in keep pile
    assert any(m.was_error for m in keep)
    assert not any(m.was_error for m in summarize)


def test_selector_summarizes_large_tool_outputs():
    """Large tool outputs (>1000 tokens) are marked for summarization."""
    selector = SmartContentSelector(recent_window_turns=10)

    # Create 22 messages to push the first one outside recent window (10 turns = 20 messages)
    messages = [
        create_message(
            role="tool",
            tool_name="read_file",
            content="x" * 2000,  # Large output
            token_count=2000,
            turn=0,  # Old message (will be outside recent window)
        )
    ]
    # Add 22 more messages (11 turns) to push first message outside recent window
    for i in range(22):
        messages.append(create_message(turn=i // 2 + 1))

    keep, summarize = selector.classify_messages(messages)

    # Large output should be summarized
    assert len(summarize) >= 1
    assert messages[0] in summarize


def test_importance_scoring():
    """Importance score reflects message characteristics."""
    selector = SmartContentSelector(recent_window_turns=0)

    # User question gets bonus
    question_msg = create_message(role="user", content="How do I fix this?")
    assert selector._calculate_importance_score(question_msg) > 0.5

    # Code block gets bonus
    code_msg = create_message(content="Here's the fix:\n```python\nprint('hi')\n```")
    assert selector._calculate_importance_score(code_msg) > 0.5

    # Large file read gets penalty
    file_msg = create_message(
        role="tool",
        tool_name="read_file",
        token_count=1000
    )
    assert selector._calculate_importance_score(file_msg) < 0.5


def test_empty_messages():
    """Empty message list returns empty piles."""
    selector = SmartContentSelector()
    keep, summarize = selector.classify_messages([])
    assert keep == []
    assert summarize == []
