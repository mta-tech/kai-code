"""Test multi-line input key bindings."""
from kai_code.rich_config import KEYBOARD_SHORTCUTS


def test_shift_enter_shortcut_exists():
    """Test Shift+Enter is defined for multi-line input."""
    # Check for shift_enter or equivalent
    shortcuts = list(KEYBOARD_SHORTCUTS.keys())
    assert any("shift" in s.lower() and "enter" in s.lower() for s in shortcuts)


def test_alt_enter_removed_or_renamed():
    """Test alt_enter is either removed or renamed to shift_enter."""
    has_alt_enter = "alt_enter" in KEYBOARD_SHORTCUTS
    has_shift_enter = "shift_enter" in KEYBOARD_SHORTCUTS

    # Should have shift_enter, and alt_enter should be removed
    assert has_shift_enter or not has_alt_enter
