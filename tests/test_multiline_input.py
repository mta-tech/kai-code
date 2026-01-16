"""Test multi-line input key bindings."""
from kai_code.rich_config import KEYBOARD_SHORTCUTS


def test_ctrl_j_shortcut_exists():
    """Test Ctrl+J is defined for multi-line input."""
    assert "ctrl_j" in KEYBOARD_SHORTCUTS
    assert KEYBOARD_SHORTCUTS["ctrl_j"]["key"] == "Ctrl+J"
    assert "newline" in KEYBOARD_SHORTCUTS["ctrl_j"]["description"].lower()


def test_shift_enter_removed():
    """Test shift_enter is removed (s-enter is not valid in prompt_toolkit)."""
    # shift_enter should not exist since s-enter is invalid
    assert "shift_enter" not in KEYBOARD_SHORTCUTS


def test_invalid_bindings_removed():
    """Test that invalid key binding patterns are not present."""
    # Check that we don't have any invalid shift+modifier patterns
    invalid_patterns = ["s-enter", "shift-enter", "s-return", "shift-return"]
    for key_name in KEYBOARD_SHORTCUTS:
        key_def = KEYBOARD_SHORTCUTS[key_name]
        key_value = key_def.get("key", "").lower()
        for invalid in invalid_patterns:
            assert invalid not in key_value, f"Invalid key pattern {invalid} found in {key_name}"
