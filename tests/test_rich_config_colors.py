"""Test rich config color definitions."""
from kai_code.rich_config import COLORS


def test_critical_color_defined():
    """Test critical color is defined for high-severity messages."""
    assert "token_critical" in COLORS
    assert "token_warning" in COLORS


def test_colors_are_valid_hex():
    """Test colors are valid hex values."""
    for name, color in COLORS.items():
        if color and color.startswith("#"):
            assert len(color) in [4, 7], f"{name}: {color} should be 3 or 6 digit hex"


def test_semantic_colors_exist():
    """Test required semantic colors exist."""
    required = ["success", "warning", "error", "info", "dim", "primary", "accent"]
    for color in required:
        assert color in COLORS, f"Missing required color: {color}"
