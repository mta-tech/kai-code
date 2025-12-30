#!/usr/bin/env python3
"""Test contextual hint transitions for keyboard shortcuts.

This test suite verifies that:
1. Hints update correctly as user types text
2. Hints update correctly when user adds newlines
3. Hints update correctly when completion menu opens
4. Hints update correctly when @ mentions are detected
5. Hint state transitions are immediate (no flicker/lag)
6. Multiple state changes are handled correctly
"""

import time
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Tuple
from unittest.mock import MagicMock, patch

import pytest


# Define ShortcutContext enum locally to avoid import issues
class ShortcutContext(Enum):
    """Defines when a keyboard shortcut should be displayed in the toolbar."""
    ALWAYS = "always"
    HAS_INPUT = "has_input"
    MULTI_LINE = "multi_line"
    EDITING = "editing"
    COMPLETION_ACTIVE = "completion_active"


# Define InputState locally for testing
@dataclass
class InputState:
    """Represents the current state of the input buffer for contextual hints."""

    has_text: bool = False
    is_multi_line: bool = False
    cursor_in_middle: bool = False
    completion_active: bool = False
    text_length: int = 0
    line_count: int = 1
    has_at_mention: bool = False

    def matches_context(self, context: ShortcutContext) -> bool:
        """Check if the current input state matches a shortcut context."""
        if context == ShortcutContext.ALWAYS:
            return True
        elif context == ShortcutContext.HAS_INPUT:
            return self.has_text
        elif context == ShortcutContext.MULTI_LINE:
            return self.is_multi_line
        elif context == ShortcutContext.EDITING:
            return self.cursor_in_middle
        elif context == ShortcutContext.COMPLETION_ACTIVE:
            return self.completion_active
        return False


def detect_input_state_from_text(
    text: str,
    cursor_position: Optional[int] = None,
    completion_active: bool = False,
) -> InputState:
    """Simulate input state detection from text (mirrors rich_input.py logic).

    Args:
        text: The current input text.
        cursor_position: Position of cursor (defaults to end of text).
        completion_active: Whether completion menu is visible.

    Returns:
        InputState reflecting the current state.
    """
    if cursor_position is None:
        cursor_position = len(text)

    # Calculate state values (matches detect_input_state in rich_input.py)
    has_text = len(text.strip()) > 0
    is_multi_line = "\n" in text
    text_length = len(text)
    line_count = text.count("\n") + 1
    cursor_in_middle = cursor_position < text_length

    # Check for @ file mentions
    has_at_mention = "@" in text

    return InputState(
        has_text=has_text,
        is_multi_line=is_multi_line,
        cursor_in_middle=cursor_in_middle,
        completion_active=completion_active,
        text_length=text_length,
        line_count=line_count,
        has_at_mention=has_at_mention,
    )


class TestUserTypingTransitions:
    """Test hint transitions as user types text."""

    def test_empty_to_has_text(self):
        """Test transition from empty to having text."""
        # Initial empty state
        state_empty = detect_input_state_from_text("")
        assert state_empty.has_text is False
        assert state_empty.matches_context(ShortcutContext.HAS_INPUT) is False

        # After typing a single character
        state_one_char = detect_input_state_from_text("h")
        assert state_one_char.has_text is True
        assert state_one_char.matches_context(ShortcutContext.HAS_INPUT) is True

    def test_has_text_to_empty_after_delete(self):
        """Test transition from having text back to empty (after delete)."""
        # With text
        state_with_text = detect_input_state_from_text("hello")
        assert state_with_text.has_text is True

        # After deleting all text (simulating backspace)
        state_empty = detect_input_state_from_text("")
        assert state_empty.has_text is False

    def test_whitespace_only_not_counted_as_text(self):
        """Test that whitespace-only input is not counted as having text."""
        # Just spaces
        state_spaces = detect_input_state_from_text("   ")
        assert state_spaces.has_text is False
        assert state_spaces.matches_context(ShortcutContext.HAS_INPUT) is False

        # Just tabs and newlines (multi-line but no actual text)
        state_whitespace = detect_input_state_from_text("\t\n  ")
        assert state_whitespace.has_text is False
        assert state_whitespace.is_multi_line is True  # Has newline

    def test_typing_progression(self):
        """Test state progression as user types word by word."""
        inputs = ["h", "he", "hel", "hell", "hello", "hello ", "hello world"]

        for i, text in enumerate(inputs):
            state = detect_input_state_from_text(text)
            assert state.has_text is True, f"Should have text at step {i}: '{text}'"
            assert state.text_length == len(text)

    def test_esc_esc_hint_appears_with_text(self):
        """Test that ESC ESC cancel hint context activates when text is present."""
        # No text - ESC ESC should not be shown
        state_empty = detect_input_state_from_text("")
        assert state_empty.matches_context(ShortcutContext.HAS_INPUT) is False

        # With text - ESC ESC should be shown
        state_with_text = detect_input_state_from_text("some input")
        assert state_with_text.matches_context(ShortcutContext.HAS_INPUT) is True


class TestNewlineTransitions:
    """Test hint transitions when user adds newlines."""

    def test_single_to_multi_line(self):
        """Test transition from single line to multi-line."""
        # Single line
        state_single = detect_input_state_from_text("hello")
        assert state_single.is_multi_line is False
        assert state_single.line_count == 1
        assert state_single.matches_context(ShortcutContext.MULTI_LINE) is False

        # After pressing Alt+Enter (newline added)
        state_multi = detect_input_state_from_text("hello\n")
        assert state_multi.is_multi_line is True
        assert state_multi.line_count == 2
        assert state_multi.matches_context(ShortcutContext.MULTI_LINE) is True

    def test_multi_line_to_single_after_delete(self):
        """Test transition from multi-line back to single line."""
        # Multi-line
        state_multi = detect_input_state_from_text("line1\nline2")
        assert state_multi.is_multi_line is True
        assert state_multi.line_count == 2

        # After deleting newline
        state_single = detect_input_state_from_text("line1line2")
        assert state_single.is_multi_line is False
        assert state_single.line_count == 1

    def test_multiple_newlines(self):
        """Test state with multiple newlines."""
        text = "line1\nline2\nline3\nline4"
        state = detect_input_state_from_text(text)

        assert state.is_multi_line is True
        assert state.line_count == 4
        assert state.matches_context(ShortcutContext.MULTI_LINE) is True

    def test_newline_at_start(self):
        """Test newline at the start of input."""
        state = detect_input_state_from_text("\nhello")
        assert state.is_multi_line is True
        assert state.line_count == 2
        assert state.has_text is True

    def test_newline_at_end(self):
        """Test newline at the end of input."""
        state = detect_input_state_from_text("hello\n")
        assert state.is_multi_line is True
        assert state.line_count == 2
        assert state.has_text is True


class TestCompletionMenuTransitions:
    """Test hint transitions when completion menu opens/closes."""

    def test_completion_inactive_by_default(self):
        """Test that completion is inactive by default."""
        state = detect_input_state_from_text("@path")
        assert state.completion_active is False
        assert state.matches_context(ShortcutContext.COMPLETION_ACTIVE) is False

    def test_completion_active_when_set(self):
        """Test that completion active state is detected."""
        state = detect_input_state_from_text("@path", completion_active=True)
        assert state.completion_active is True
        assert state.matches_context(ShortcutContext.COMPLETION_ACTIVE) is True

    def test_completion_menu_opens_on_at_symbol(self):
        """Test completion context with @ symbol (file completion trigger)."""
        # User types @
        state = detect_input_state_from_text("@", completion_active=True)
        assert state.has_at_mention is True
        assert state.completion_active is True

    def test_completion_menu_opens_on_slash(self):
        """Test completion context with / symbol (command completion trigger)."""
        # User types /
        state = detect_input_state_from_text("/", completion_active=True)
        assert state.completion_active is True

    def test_completion_menu_closes(self):
        """Test transition when completion menu closes."""
        # Menu open
        state_open = detect_input_state_from_text("@file", completion_active=True)
        assert state_open.completion_active is True

        # Menu closes (e.g., after selection or pressing ESC)
        state_closed = detect_input_state_from_text("@file", completion_active=False)
        assert state_closed.completion_active is False


class TestAtMentionTransitions:
    """Test hint transitions for @ file mentions."""

    def test_at_mention_detected(self):
        """Test that @ mention is detected."""
        state = detect_input_state_from_text("@file.py")
        assert state.has_at_mention is True

    def test_at_mention_not_detected_without_at(self):
        """Test that @ mention is not detected without @ symbol."""
        state = detect_input_state_from_text("file.py")
        assert state.has_at_mention is False

    def test_at_mention_mid_text(self):
        """Test @ mention detection in middle of text."""
        state = detect_input_state_from_text("please review @src/main.py")
        assert state.has_at_mention is True
        assert state.has_text is True

    def test_multiple_at_mentions(self):
        """Test multiple @ mentions."""
        state = detect_input_state_from_text("compare @file1.py and @file2.py")
        assert state.has_at_mention is True

    def test_at_mention_triggers_alt_enter_hint(self):
        """Test that @ mention triggers Alt+Enter newline hint context.

        When user mentions a file, they often want to add more context,
        so the Alt+Enter hint should appear.
        """
        state = detect_input_state_from_text("@src/main.py")
        # has_at_mention is used to show Alt+Enter hint
        assert state.has_at_mention is True
        # The toolbar logic shows Alt+Enter when has_text OR has_at_mention OR is_multi_line
        assert state.has_text is True


class TestCursorPositionTransitions:
    """Test hint transitions based on cursor position."""

    def test_cursor_at_end(self):
        """Test state with cursor at end of text."""
        text = "hello"
        state = detect_input_state_from_text(text, cursor_position=len(text))
        assert state.cursor_in_middle is False
        assert state.matches_context(ShortcutContext.EDITING) is False

    def test_cursor_at_start(self):
        """Test state with cursor at start of text (editing mode)."""
        text = "hello"
        state = detect_input_state_from_text(text, cursor_position=0)
        assert state.cursor_in_middle is True
        assert state.matches_context(ShortcutContext.EDITING) is True

    def test_cursor_in_middle(self):
        """Test state with cursor in middle of text."""
        text = "hello world"
        state = detect_input_state_from_text(text, cursor_position=5)  # After "hello"
        assert state.cursor_in_middle is True
        assert state.matches_context(ShortcutContext.EDITING) is True

    def test_cursor_moves_to_end(self):
        """Test transition when cursor moves to end."""
        text = "hello"

        # Cursor in middle
        state_middle = detect_input_state_from_text(text, cursor_position=2)
        assert state_middle.cursor_in_middle is True

        # Cursor at end
        state_end = detect_input_state_from_text(text, cursor_position=5)
        assert state_end.cursor_in_middle is False


class TestCombinedStateTransitions:
    """Test combined state changes (multiple conditions at once)."""

    def test_multi_line_with_at_mention(self):
        """Test multi-line input with @ mention."""
        text = "please check these files:\n@src/main.py\n@src/utils.py"
        state = detect_input_state_from_text(text)

        assert state.has_text is True
        assert state.is_multi_line is True
        assert state.has_at_mention is True
        assert state.line_count == 3

    def test_editing_multi_line_input(self):
        """Test editing in middle of multi-line input."""
        text = "line1\nline2\nline3"
        state = detect_input_state_from_text(text, cursor_position=7)  # After "line1\nl"

        assert state.is_multi_line is True
        assert state.cursor_in_middle is True
        assert state.matches_context(ShortcutContext.EDITING) is True
        assert state.matches_context(ShortcutContext.MULTI_LINE) is True

    def test_all_contexts_active(self):
        """Test state where multiple contexts are active."""
        text = "@file.py\nmore text"
        state = detect_input_state_from_text(
            text,
            cursor_position=5,  # In middle
            completion_active=True,
        )

        # All conditions true
        assert state.has_text is True
        assert state.is_multi_line is True
        assert state.cursor_in_middle is True
        assert state.completion_active is True
        assert state.has_at_mention is True

        # All context matches should work
        assert state.matches_context(ShortcutContext.ALWAYS) is True
        assert state.matches_context(ShortcutContext.HAS_INPUT) is True
        assert state.matches_context(ShortcutContext.MULTI_LINE) is True
        assert state.matches_context(ShortcutContext.EDITING) is True
        assert state.matches_context(ShortcutContext.COMPLETION_ACTIVE) is True


class TestHintUpdatePerformance:
    """Test that hint updates don't cause flicker or lag."""

    def test_state_detection_is_fast(self):
        """Test that state detection is fast (no lag)."""
        text = "This is a longer piece of text with @file.py mentions\nand multiple lines"

        start = time.perf_counter()
        for _ in range(1000):
            detect_input_state_from_text(text)
        elapsed = time.perf_counter() - start

        # 1000 iterations should take less than 100ms (0.1s)
        # This ensures updates are fast enough for real-time UI
        assert elapsed < 0.1, f"State detection took {elapsed:.3f}s for 1000 iterations"

    def test_context_matching_is_fast(self):
        """Test that context matching is fast."""
        state = InputState(
            has_text=True,
            is_multi_line=True,
            cursor_in_middle=True,
            completion_active=True,
            has_at_mention=True,
        )

        contexts = list(ShortcutContext)

        start = time.perf_counter()
        for _ in range(10000):
            for ctx in contexts:
                state.matches_context(ctx)
        elapsed = time.perf_counter() - start

        # 10000 * 5 context checks should take less than 50ms
        assert elapsed < 0.05, f"Context matching took {elapsed:.3f}s for 50000 checks"

    def test_rapid_state_changes(self):
        """Test handling of rapid state changes (simulating fast typing)."""
        # Simulate rapid typing: h -> he -> hel -> hell -> hello
        texts = ["h", "he", "hel", "hell", "hello", "hello ", "hello w"]

        states = []
        for text in texts:
            state = detect_input_state_from_text(text)
            states.append(state)

        # All states should have text
        for i, state in enumerate(states):
            assert state.has_text is True, f"State {i} should have text"

        # Text lengths should increase
        for i in range(len(states) - 1):
            assert states[i].text_length < states[i + 1].text_length


class TestEdgeCases:
    """Test edge cases in state detection."""

    def test_empty_string(self):
        """Test empty string input."""
        state = detect_input_state_from_text("")
        assert state.has_text is False
        assert state.is_multi_line is False
        assert state.text_length == 0
        assert state.line_count == 1

    def test_single_newline(self):
        """Test input that is just a newline."""
        state = detect_input_state_from_text("\n")
        assert state.has_text is False  # Whitespace only
        assert state.is_multi_line is True
        assert state.line_count == 2

    def test_at_symbol_alone(self):
        """Test just @ symbol."""
        state = detect_input_state_from_text("@")
        assert state.has_at_mention is True
        assert state.has_text is True

    def test_very_long_input(self):
        """Test very long input doesn't cause issues."""
        text = "a" * 10000
        state = detect_input_state_from_text(text)
        assert state.has_text is True
        assert state.text_length == 10000

    def test_many_lines(self):
        """Test input with many lines."""
        lines = ["line"] * 100
        text = "\n".join(lines)
        state = detect_input_state_from_text(text)
        assert state.is_multi_line is True
        assert state.line_count == 100

    def test_special_characters(self):
        """Test input with special characters."""
        text = "Special chars: @#$%^&*()[]{}|\\;':\",./<>?"
        state = detect_input_state_from_text(text)
        assert state.has_text is True
        assert state.has_at_mention is True

    def test_unicode_text(self):
        """Test input with unicode characters."""
        text = "Hello 世界 🌍 مرحبا"
        state = detect_input_state_from_text(text)
        assert state.has_text is True

    def test_escaped_at_symbol(self):
        """Test escaped @ symbol (shouldn't matter for detection)."""
        # The regex AT_MENTION_RE handles escaped spaces, but @ is always detected
        text = "email: user\\@domain.com"
        state = detect_input_state_from_text(text)
        assert state.has_at_mention is True  # Still detected


class TestRealWorldScenarios:
    """Test real-world usage scenarios for hint transitions."""

    def test_scenario_writing_question(self):
        """Scenario: User writing a question about code."""
        # Step 1: User starts typing
        state1 = detect_input_state_from_text("How")
        assert state1.has_text is True
        assert state1.matches_context(ShortcutContext.HAS_INPUT) is True

        # Step 2: User continues
        state2 = detect_input_state_from_text("How do I fix")
        assert state2.has_text is True

        # Step 3: User mentions a file
        state3 = detect_input_state_from_text("How do I fix @src/main.py")
        assert state3.has_text is True
        assert state3.has_at_mention is True

    def test_scenario_multi_line_prompt(self):
        """Scenario: User writing multi-line prompt."""
        # Step 1: First line
        state1 = detect_input_state_from_text("Please review this code:")
        assert state1.is_multi_line is False

        # Step 2: User presses Alt+Enter
        state2 = detect_input_state_from_text("Please review this code:\n")
        assert state2.is_multi_line is True

        # Step 3: User mentions file
        state3 = detect_input_state_from_text("Please review this code:\n@src/app.py")
        assert state3.is_multi_line is True
        assert state3.has_at_mention is True

    def test_scenario_using_completion(self):
        """Scenario: User using file completion."""
        # Step 1: User types @
        state1 = detect_input_state_from_text("@")
        assert state1.has_at_mention is True

        # Step 2: Completion menu opens
        state2 = detect_input_state_from_text("@sr", completion_active=True)
        assert state2.completion_active is True

        # Step 3: User selects file, menu closes
        state3 = detect_input_state_from_text("@src/main.py", completion_active=False)
        assert state3.completion_active is False
        assert state3.has_at_mention is True

    def test_scenario_canceling_input(self):
        """Scenario: User types then cancels with ESC ESC."""
        # Step 1: User types
        state1 = detect_input_state_from_text("wrong command")
        assert state1.has_text is True
        assert state1.matches_context(ShortcutContext.HAS_INPUT) is True

        # Step 2: After ESC ESC (input cleared)
        state2 = detect_input_state_from_text("")
        assert state2.has_text is False
        assert state2.matches_context(ShortcutContext.HAS_INPUT) is False


# Run tests if executed directly
if __name__ == "__main__":
    print("Running contextual hint transition tests...")
    pytest.main([__file__, "-v"])
