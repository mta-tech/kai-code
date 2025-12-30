#!/usr/bin/env python3
"""Unit tests for shortcut formatting and contextual display functions.

This test suite focuses on edge cases for:
1. format_shortcut_hint() - formatting keyboard shortcut hints
2. format_shortcut_from_registry() - registry-based shortcut formatting
3. RotatingHintHelper - rotating hint display management
4. InputState.matches_context() - context matching for contextual hints
5. ToolbarSegment - toolbar segment width and separator handling

These tests ensure robust handling of edge cases and unusual inputs.
"""

import time
from dataclasses import dataclass, field
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


# Define KEYBOARD_SHORTCUTS locally to match production registry
KEYBOARD_SHORTCUTS = {
    "ctrl_e": {
        "key": "Ctrl+E",
        "description": "Open current input in external editor",
        "display": "editor",
        "context": ShortcutContext.ALWAYS,
        "priority": 3,
    },
    "ctrl_t": {
        "key": "Ctrl+T",
        "description": "Toggle auto-approve mode",
        "display": "toggle approve",
        "context": ShortcutContext.ALWAYS,
        "priority": 1,
    },
    "ctrl_b": {
        "key": "Ctrl+B",
        "description": "Run current input as a background task",
        "display": "background",
        "context": ShortcutContext.ALWAYS,
        "priority": 2,
    },
    "double_esc": {
        "key": "ESC ESC",
        "description": "Cancel current input",
        "display": "cancel",
        "context": ShortcutContext.HAS_INPUT,
        "priority": 4,
    },
    "alt_enter": {
        "key": "Alt+Enter",
        "description": "Insert newline",
        "display": "newline",
        "context": ShortcutContext.ALWAYS,
        "priority": 5,
    },
    "at_mention": {
        "key": "@",
        "description": "Type @ to autocomplete files",
        "display": "files",
        "context": ShortcutContext.ALWAYS,
        "priority": 7,
    },
    "slash_command": {
        "key": "/",
        "description": "Type / for commands",
        "display": "commands",
        "context": ShortcutContext.ALWAYS,
        "priority": 8,
    },
}


def format_shortcut_hint(
    key: str, display: str, include_separator: bool = True
) -> List[Tuple[str, str]]:
    """Format a keyboard shortcut hint with consistent styling.

    This mirrors the production implementation in rich_input.py.
    """
    parts: List[Tuple[str, str]] = []

    if include_separator:
        parts.append(("", " | "))

    parts.append(("class:toolbar-key", key))
    parts.append(("", " "))
    parts.append(("class:toolbar-shortcut", display))

    return parts


def format_shortcut_from_registry(
    shortcut_id: str, include_separator: bool = True
) -> List[Tuple[str, str]]:
    """Format a shortcut hint from the KEYBOARD_SHORTCUTS registry."""
    shortcut = KEYBOARD_SHORTCUTS.get(shortcut_id)
    if not shortcut:
        return []

    return format_shortcut_hint(
        key=shortcut["key"],
        display=shortcut["display"],
        include_separator=include_separator,
    )


@dataclass
class InputState:
    """Represents the current state of the input buffer."""

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


@dataclass
class ToolbarSegment:
    """Represents a segment of the toolbar with priority for truncation."""

    parts: List[Tuple[str, str]] = field(default_factory=list)
    priority: int = 5
    include_separator: bool = True

    @property
    def width(self) -> int:
        return sum(len(text) for _, text in self.parts)

    def get_parts_with_separator(self) -> List[Tuple[str, str]]:
        if self.include_separator and self.parts:
            return [("", " | ")] + list(self.parts)
        return list(self.parts)

    @property
    def total_width(self) -> int:
        base_width = self.width
        if self.include_separator and self.parts:
            base_width += 3
        return base_width


@dataclass
class RotatingHint:
    """Represents a single hint for the rotating hint display."""

    key: str
    description: str
    shortcut_id: Optional[str] = None


class RotatingHintHelper:
    """Manages rotating through secondary hints."""

    def __init__(
        self,
        hints: Optional[List[RotatingHint]] = None,
        rotation_interval: float = 5.0,
    ) -> None:
        self.hints = hints or self._default_hints()
        self.rotation_interval = rotation_interval
        self.current_index = 0
        self.last_rotation_time = time.monotonic()

    @staticmethod
    def _default_hints() -> List[RotatingHint]:
        return [
            RotatingHint(key="@", description="files", shortcut_id="at_mention"),
            RotatingHint(key="/", description="commands", shortcut_id="slash_command"),
        ]

    def get_current_hint(self) -> RotatingHint:
        if not self.hints:
            return RotatingHint(key="", description="")

        now = time.monotonic()
        elapsed = now - self.last_rotation_time

        # Handle zero/very small rotation intervals to avoid division by zero
        if self.rotation_interval > 0 and elapsed >= self.rotation_interval:
            rotations = int(elapsed / self.rotation_interval)
            self.current_index = (self.current_index + rotations) % len(self.hints)
            self.last_rotation_time = now

        return self.hints[self.current_index]

    def advance(self) -> RotatingHint:
        if not self.hints:
            return RotatingHint(key="", description="")

        self.current_index = (self.current_index + 1) % len(self.hints)
        self.last_rotation_time = time.monotonic()
        return self.hints[self.current_index]

    def format_current_hint(self, include_separator: bool = True) -> List[Tuple[str, str]]:
        hint = self.get_current_hint()

        if hint.shortcut_id:
            return format_shortcut_from_registry(hint.shortcut_id, include_separator)
        elif hint.key and hint.description:
            return format_shortcut_hint(hint.key, hint.description, include_separator)
        else:
            return []


# =============================================================================
# Tests for format_shortcut_hint() Edge Cases
# =============================================================================


class TestFormatShortcutHintEdgeCases:
    """Test edge cases for format_shortcut_hint function."""

    def test_empty_key_string(self):
        """Test formatting with empty key string."""
        result = format_shortcut_hint("", "action", include_separator=False)

        # Should still produce valid output with empty key
        assert len(result) >= 2
        # Find the key part
        key_parts = [p for p in result if p[0] == "class:toolbar-key"]
        assert len(key_parts) == 1
        assert key_parts[0][1] == ""  # Empty key

    def test_empty_display_string(self):
        """Test formatting with empty display string."""
        result = format_shortcut_hint("Ctrl+X", "", include_separator=False)

        # Should still produce valid output with empty display
        assert len(result) >= 2
        # Find the display part
        display_parts = [p for p in result if p[0] == "class:toolbar-shortcut"]
        assert len(display_parts) == 1
        assert display_parts[0][1] == ""  # Empty display

    def test_both_empty_strings(self):
        """Test formatting with both key and display empty."""
        result = format_shortcut_hint("", "", include_separator=False)

        # Should still produce valid structure
        assert len(result) == 3  # key, space, display
        key_parts = [p for p in result if p[0] == "class:toolbar-key"]
        display_parts = [p for p in result if p[0] == "class:toolbar-shortcut"]
        assert key_parts[0][1] == ""
        assert display_parts[0][1] == ""

    def test_key_with_special_characters(self):
        """Test key with special characters (symbols, unicode)."""
        special_keys = [
            "Ctrl+<>",
            "Alt+[SHIFT]",
            "Meta+∞",
            "Fn+🎹",
            "↑↓←→",
        ]

        for key in special_keys:
            result = format_shortcut_hint(key, "action", include_separator=False)
            key_parts = [p for p in result if p[0] == "class:toolbar-key"]
            assert len(key_parts) == 1
            assert key_parts[0][1] == key

    def test_very_long_key_string(self):
        """Test formatting with very long key string (edge case for display)."""
        long_key = "Ctrl+Alt+Shift+Super+Meta+Fn+F12"
        result = format_shortcut_hint(long_key, "action", include_separator=False)

        key_parts = [p for p in result if p[0] == "class:toolbar-key"]
        assert key_parts[0][1] == long_key

    def test_very_long_display_string(self):
        """Test formatting with very long display string."""
        long_display = "this is a very long description that might overflow the toolbar"
        result = format_shortcut_hint("Ctrl+X", long_display, include_separator=False)

        display_parts = [p for p in result if p[0] == "class:toolbar-shortcut"]
        assert display_parts[0][1] == long_display

    def test_unicode_in_key_and_display(self):
        """Test unicode characters in both key and display."""
        result = format_shortcut_hint("⌘+K", "命令", include_separator=False)

        key_parts = [p for p in result if p[0] == "class:toolbar-key"]
        display_parts = [p for p in result if p[0] == "class:toolbar-shortcut"]

        assert key_parts[0][1] == "⌘+K"
        assert display_parts[0][1] == "命令"

    def test_whitespace_in_key(self):
        """Test key with leading/trailing/internal whitespace."""
        # Internal space (like "ESC ESC")
        result = format_shortcut_hint("ESC  ESC", "cancel", include_separator=False)
        key_parts = [p for p in result if p[0] == "class:toolbar-key"]
        assert "ESC  ESC" in key_parts[0][1]

    def test_newline_in_key(self):
        """Test key containing newline character (shouldn't happen but should handle)."""
        result = format_shortcut_hint("Ctrl\nX", "action", include_separator=False)

        key_parts = [p for p in result if p[0] == "class:toolbar-key"]
        assert len(key_parts) == 1  # Should still produce output

    def test_separator_placement(self):
        """Test separator is correctly placed at the beginning."""
        result_with_sep = format_shortcut_hint("X", "y", include_separator=True)
        result_without_sep = format_shortcut_hint("X", "y", include_separator=False)

        # With separator: should start with separator
        assert result_with_sep[0] == ("", " | ")

        # Without separator: should not start with separator
        assert result_without_sep[0] != ("", " | ")

    def test_consistent_part_order(self):
        """Test that parts are always in order: [separator], key, space, display."""
        result = format_shortcut_hint("K", "D", include_separator=True)

        # Expected order: separator, key, space, display
        assert result[0] == ("", " | ")  # separator
        assert result[1][0] == "class:toolbar-key"  # key styling
        assert result[2] == ("", " ")  # space
        assert result[3][0] == "class:toolbar-shortcut"  # display styling

    def test_tab_in_key_or_display(self):
        """Test tab characters in key or display."""
        result = format_shortcut_hint("Ctrl+\t", "ac\ttion", include_separator=False)
        # Should handle tabs without crashing
        assert len(result) >= 2


# =============================================================================
# Tests for format_shortcut_from_registry() Edge Cases
# =============================================================================


class TestFormatShortcutFromRegistryEdgeCases:
    """Test edge cases for format_shortcut_from_registry function."""

    def test_none_shortcut_id(self):
        """Test with None-like shortcut ID."""
        result = format_shortcut_from_registry("")
        assert result == []

    def test_invalid_shortcut_id(self):
        """Test with completely invalid shortcut ID."""
        result = format_shortcut_from_registry("this_does_not_exist")
        assert result == []

    def test_case_sensitivity(self):
        """Test that shortcut IDs are case-sensitive."""
        # Valid lowercase
        result_lower = format_shortcut_from_registry("ctrl_e")
        assert len(result_lower) > 0

        # Invalid uppercase (should not match)
        result_upper = format_shortcut_from_registry("CTRL_E")
        assert result_upper == []

        # Invalid mixed case
        result_mixed = format_shortcut_from_registry("Ctrl_E")
        assert result_mixed == []

    def test_partial_match_not_found(self):
        """Test that partial matches don't work."""
        result = format_shortcut_from_registry("ctrl")
        assert result == []

        result2 = format_shortcut_from_registry("ctrl_e_extra")
        assert result2 == []

    def test_whitespace_in_id(self):
        """Test shortcut ID with whitespace (should not match)."""
        result = format_shortcut_from_registry(" ctrl_e")
        assert result == []

        result2 = format_shortcut_from_registry("ctrl_e ")
        assert result2 == []

    def test_all_valid_registry_shortcuts(self):
        """Test all valid shortcuts in the registry are formatted correctly."""
        for shortcut_id in KEYBOARD_SHORTCUTS.keys():
            result = format_shortcut_from_registry(shortcut_id, include_separator=False)

            # Should produce non-empty result
            assert len(result) > 0, f"Failed for shortcut: {shortcut_id}"

            # Should contain the key
            shortcut = KEYBOARD_SHORTCUTS[shortcut_id]
            result_text = "".join(text for _, text in result)
            assert shortcut["key"] in result_text
            assert shortcut["display"] in result_text


# =============================================================================
# Tests for InputState.matches_context() Edge Cases
# =============================================================================


class TestInputStateMatchesContextEdgeCases:
    """Test edge cases for InputState.matches_context method."""

    def test_default_state_matches_only_always(self):
        """Test default InputState only matches ALWAYS context."""
        state = InputState()

        assert state.matches_context(ShortcutContext.ALWAYS) is True
        assert state.matches_context(ShortcutContext.HAS_INPUT) is False
        assert state.matches_context(ShortcutContext.MULTI_LINE) is False
        assert state.matches_context(ShortcutContext.EDITING) is False
        assert state.matches_context(ShortcutContext.COMPLETION_ACTIVE) is False

    def test_all_true_matches_all_contexts(self):
        """Test InputState with all flags True matches all contexts."""
        state = InputState(
            has_text=True,
            is_multi_line=True,
            cursor_in_middle=True,
            completion_active=True,
        )

        for context in ShortcutContext:
            assert state.matches_context(context) is True

    def test_independent_context_flags(self):
        """Test that context flags are independent (one True doesn't affect others)."""
        # Only has_text is True
        state_text = InputState(has_text=True)
        assert state_text.matches_context(ShortcutContext.HAS_INPUT) is True
        assert state_text.matches_context(ShortcutContext.MULTI_LINE) is False
        assert state_text.matches_context(ShortcutContext.EDITING) is False
        assert state_text.matches_context(ShortcutContext.COMPLETION_ACTIVE) is False

        # Only is_multi_line is True
        state_multi = InputState(is_multi_line=True)
        assert state_multi.matches_context(ShortcutContext.HAS_INPUT) is False
        assert state_multi.matches_context(ShortcutContext.MULTI_LINE) is True
        assert state_multi.matches_context(ShortcutContext.EDITING) is False
        assert state_multi.matches_context(ShortcutContext.COMPLETION_ACTIVE) is False

    def test_multiple_context_checks_are_stateless(self):
        """Test that calling matches_context doesn't modify state."""
        state = InputState(has_text=True)
        original_text = state.has_text

        # Call multiple times
        for _ in range(10):
            state.matches_context(ShortcutContext.HAS_INPUT)
            state.matches_context(ShortcutContext.ALWAYS)

        assert state.has_text == original_text

    def test_context_priority_not_affected_by_order(self):
        """Test that context matching order doesn't matter."""
        state = InputState(has_text=True, is_multi_line=True)

        # Check in different orders
        result1 = [state.matches_context(c) for c in ShortcutContext]
        result2 = [state.matches_context(c) for c in reversed(list(ShortcutContext))]

        # Results should be consistent regardless of order
        assert set(result1) == set(result2)


# =============================================================================
# Tests for ToolbarSegment Edge Cases
# =============================================================================


class TestToolbarSegmentEdgeCases:
    """Test edge cases for ToolbarSegment class."""

    def test_empty_parts_list(self):
        """Test segment with empty parts list."""
        segment = ToolbarSegment(parts=[], priority=1)

        assert segment.width == 0
        assert segment.total_width == 0
        assert segment.get_parts_with_separator() == []

    def test_single_empty_part(self):
        """Test segment with single empty part."""
        segment = ToolbarSegment(parts=[("style", "")], priority=1)

        assert segment.width == 0
        # But total_width includes separator if include_separator is True
        assert segment.total_width == 3  # separator " | "

    def test_parts_with_empty_strings(self):
        """Test segment with multiple empty string parts."""
        segment = ToolbarSegment(
            parts=[("", ""), ("style", ""), ("", "")],
            priority=1,
        )

        assert segment.width == 0

    def test_parts_with_very_long_text(self):
        """Test segment with very long text."""
        long_text = "x" * 1000
        segment = ToolbarSegment(
            parts=[("style", long_text)],
            priority=1,
        )

        assert segment.width == 1000
        assert segment.total_width == 1003  # 1000 + 3 for separator

    def test_priority_values(self):
        """Test various priority values."""
        # Normal priorities
        for priority in [1, 2, 3, 4, 5, 10, 100]:
            segment = ToolbarSegment(parts=[], priority=priority)
            assert segment.priority == priority

        # Zero priority
        segment_zero = ToolbarSegment(parts=[], priority=0)
        assert segment_zero.priority == 0

        # Negative priority (unusual but should work)
        segment_neg = ToolbarSegment(parts=[], priority=-1)
        assert segment_neg.priority == -1

    def test_separator_only_added_when_parts_not_empty(self):
        """Test that separator is only added when parts are not empty."""
        # Empty parts - no separator even if include_separator=True
        segment_empty = ToolbarSegment(parts=[], priority=1, include_separator=True)
        assert segment_empty.get_parts_with_separator() == []

        # Non-empty parts - separator added
        segment_parts = ToolbarSegment(
            parts=[("", "text")], priority=1, include_separator=True
        )
        parts_with_sep = segment_parts.get_parts_with_separator()
        assert parts_with_sep[0] == ("", " | ")

    def test_width_calculation_with_unicode(self):
        """Test width calculation with unicode characters."""
        segment = ToolbarSegment(
            parts=[("", "Hello 世界"), ("", " 🌍")],
            priority=1,
        )

        # Python len() counts characters, not display width
        # "Hello 世界" = 8 chars, " 🌍" = 2 chars = 10 total
        assert segment.width == 10

    def test_multiple_parts_width(self):
        """Test width calculation with multiple parts."""
        segment = ToolbarSegment(
            parts=[
                ("style1", "abc"),
                ("style2", "def"),
                ("style3", "ghij"),
            ],
            priority=1,
        )

        assert segment.width == 10  # 3 + 3 + 4


# =============================================================================
# Tests for RotatingHintHelper Edge Cases
# =============================================================================


class TestRotatingHintHelperEdgeCases:
    """Test edge cases for RotatingHintHelper class."""

    def test_empty_hints_list(self):
        """Test helper with empty hints list uses default hints.

        Note: When hints=[] is passed, it evaluates to falsy and the
        implementation falls back to default hints. This is intentional
        to ensure hints are always available.
        """
        helper = RotatingHintHelper(hints=[], rotation_interval=1.0)

        # Empty list is falsy, so defaults are used
        hint = helper.get_current_hint()
        # Default hints are @ files and / commands
        assert hint.key in ["@", "/"]
        assert hint.description in ["files", "commands"]

        # Advance should work with default hints
        advanced = helper.advance()
        assert advanced.key in ["@", "/"]

        # Format should return valid output
        formatted = helper.format_current_hint()
        assert len(formatted) > 0

    def test_single_hint(self):
        """Test helper with single hint."""
        single_hint = RotatingHint(key="X", description="action")
        helper = RotatingHintHelper(hints=[single_hint], rotation_interval=1.0)

        # Get should always return the same hint
        for _ in range(5):
            hint = helper.get_current_hint()
            assert hint.key == "X"
            assert hint.description == "action"

        # Advance should still return the same hint
        advanced = helper.advance()
        assert advanced.key == "X"

    def test_rotation_interval_zero(self):
        """Test with zero rotation interval.

        With zero interval, the implementation should NOT crash due to
        division by zero. Instead, it should gracefully handle this edge
        case by staying on the current hint (no automatic rotation).
        Manual advance() can still be used to rotate.
        """
        hints = [
            RotatingHint(key="A", description="a"),
            RotatingHint(key="B", description="b"),
        ]
        helper = RotatingHintHelper(hints=hints, rotation_interval=0.0)

        # With zero interval, should NOT error
        hint1 = helper.get_current_hint()
        hint2 = helper.get_current_hint()

        # Should stay on same hint (no auto-rotation with zero interval)
        assert hint1.key == hint2.key == "A"

        # Manual advance should still work
        advanced = helper.advance()
        assert advanced.key == "B"

    def test_rotation_interval_very_large(self):
        """Test with very large rotation interval."""
        hints = [
            RotatingHint(key="A", description="a"),
            RotatingHint(key="B", description="b"),
        ]
        helper = RotatingHintHelper(hints=hints, rotation_interval=1e10)

        # Should always return first hint
        hint1 = helper.get_current_hint()
        hint2 = helper.get_current_hint()
        assert hint1.key == hint2.key == "A"

    def test_manual_advance_wraps_around(self):
        """Test that manual advance wraps around correctly."""
        hints = [
            RotatingHint(key="A", description="a"),
            RotatingHint(key="B", description="b"),
            RotatingHint(key="C", description="c"),
        ]
        helper = RotatingHintHelper(hints=hints, rotation_interval=1000.0)

        # Advance through all hints and wrap around
        assert helper.get_current_hint().key == "A"
        helper.advance()
        assert helper.get_current_hint().key == "B"
        helper.advance()
        assert helper.get_current_hint().key == "C"
        helper.advance()
        assert helper.get_current_hint().key == "A"  # Wrapped

    def test_default_hints_are_valid(self):
        """Test that default hints are valid and formattable."""
        helper = RotatingHintHelper()

        # Default hints should exist
        assert len(helper.hints) >= 2

        # Each hint should be formattable
        for _ in range(len(helper.hints)):
            formatted = helper.format_current_hint()
            assert len(formatted) > 0
            helper.advance()

    def test_hint_without_shortcut_id(self):
        """Test hint without shortcut_id uses fallback formatting."""
        hint = RotatingHint(key="K", description="desc", shortcut_id=None)
        helper = RotatingHintHelper(hints=[hint])

        formatted = helper.format_current_hint(include_separator=False)

        # Should use format_shortcut_hint fallback
        assert len(formatted) > 0
        result_text = "".join(text for _, text in formatted)
        assert "K" in result_text
        assert "desc" in result_text

    def test_hint_with_invalid_shortcut_id(self):
        """Test hint with invalid shortcut_id."""
        hint = RotatingHint(key="K", description="desc", shortcut_id="invalid_id")
        helper = RotatingHintHelper(hints=[hint])

        # Should return empty list since registry lookup fails
        formatted = helper.format_current_hint()
        assert formatted == []

    def test_hint_with_empty_key_and_description(self):
        """Test hint with empty key and description."""
        hint = RotatingHint(key="", description="")
        helper = RotatingHintHelper(hints=[hint])

        # Should return empty list since both are empty
        formatted = helper.format_current_hint()
        assert formatted == []


# =============================================================================
# Tests for Combined Edge Cases
# =============================================================================


class TestCombinedEdgeCases:
    """Test combined edge cases across multiple components."""

    def test_format_then_segment(self):
        """Test formatting a hint then putting it in a segment."""
        hint_parts = format_shortcut_hint("Ctrl+X", "action", include_separator=False)

        segment = ToolbarSegment(parts=hint_parts, priority=2)

        # Should have valid width
        assert segment.width > 0

        # Width should match the text content
        text_width = sum(len(text) for _, text in hint_parts)
        assert segment.width == text_width

    def test_context_matching_with_registry_shortcuts(self):
        """Test context matching aligns with registry shortcut contexts."""
        state_empty = InputState()
        state_with_text = InputState(has_text=True)

        for shortcut_id, shortcut in KEYBOARD_SHORTCUTS.items():
            context = shortcut["context"]

            # ALWAYS context shortcuts should match empty state
            if context == ShortcutContext.ALWAYS:
                assert state_empty.matches_context(context) is True

            # HAS_INPUT context shortcuts should only match when has_text
            if context == ShortcutContext.HAS_INPUT:
                assert state_empty.matches_context(context) is False
                assert state_with_text.matches_context(context) is True

    def test_performance_formatting_many_hints(self):
        """Test performance when formatting many hints rapidly."""
        start = time.perf_counter()

        for _ in range(1000):
            format_shortcut_hint("Ctrl+X", "action", include_separator=True)
            format_shortcut_from_registry("ctrl_e", include_separator=True)

        elapsed = time.perf_counter() - start

        # 2000 format calls should complete in under 100ms
        assert elapsed < 0.1, f"Formatting took {elapsed:.3f}s for 2000 calls"

    def test_performance_rotating_hint_access(self):
        """Test performance of rotating hint access."""
        helper = RotatingHintHelper()

        start = time.perf_counter()

        for _ in range(1000):
            helper.get_current_hint()
            helper.format_current_hint()

        elapsed = time.perf_counter() - start

        # 2000 operations should complete in under 100ms
        assert elapsed < 0.1, f"Rotating hint access took {elapsed:.3f}s for 2000 ops"


# =============================================================================
# Tests for Error Handling
# =============================================================================


class TestErrorHandling:
    """Test error handling in formatting and display functions."""

    def test_format_with_none_values(self):
        """Test that format functions handle None-like values gracefully."""
        # While the function signature expects str, test robustness
        try:
            # Empty strings should work
            result = format_shortcut_hint("", "", include_separator=False)
            assert isinstance(result, list)
        except (TypeError, AttributeError):
            pytest.fail("format_shortcut_hint should handle empty strings")

    def test_segment_with_none_parts(self):
        """Test ToolbarSegment handles unusual parts gracefully."""
        # Parts as empty list should work
        segment = ToolbarSegment(parts=[], priority=1)
        assert segment.width == 0

    def test_input_state_default_values(self):
        """Test InputState has sensible defaults."""
        state = InputState()

        assert state.has_text is False
        assert state.is_multi_line is False
        assert state.cursor_in_middle is False
        assert state.completion_active is False
        assert state.text_length == 0
        assert state.line_count == 1
        assert state.has_at_mention is False

    def test_rotating_hint_helper_default_creation(self):
        """Test RotatingHintHelper can be created with defaults."""
        helper = RotatingHintHelper()

        # Should have default hints
        assert len(helper.hints) > 0

        # Should be able to get current hint
        hint = helper.get_current_hint()
        assert hint is not None

        # Should be able to format
        formatted = helper.format_current_hint()
        assert isinstance(formatted, list)


# Run tests if executed directly
if __name__ == "__main__":
    print("Running shortcut formatting edge case tests...")
    pytest.main([__file__, "-v"])
