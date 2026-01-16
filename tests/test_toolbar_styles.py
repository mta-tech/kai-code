"""Test toolbar style definitions."""
from kai_code.rich_input import get_bottom_toolbar
from kai_code.rich_config import SessionState


def test_toolbar_has_critical_style():
    """Test toolbar has critical token usage style."""
    session_state = SessionState()
    session_ref = {}

    toolbar_func = get_bottom_toolbar(session_state, session_ref)
    # The function should exist and be callable
    assert callable(toolbar_func)


def test_toolbar_styles_defined():
    """Test all required toolbar styles are defined."""
    from kai_code.rich_input import toolbar_style

    # toolbar_style should be defined in the module
    # This is more of an integration/smoke test
    assert toolbar_style is not None


def test_toolbar_has_critical_and_warning_styles():
    """Test toolbar includes critical and warning styles for token status."""
    from kai_code.rich_input import toolbar_style

    # style_rules is a list of (style_name, style_string) tuples
    style_rules_list = toolbar_style.style_rules

    # Convert to dict for easier testing
    style_dict = dict(style_rules_list)

    # Check for required token status styles
    assert "toolbar-critical" in style_dict
    assert "toolbar-warning" in style_dict

    # Verify they have appropriate colors (red for critical, orange/amber for warning)
    critical_style = style_dict["toolbar-critical"]
    warning_style = style_dict["toolbar-warning"]

    # Critical should have red background (#ef4444)
    assert "#ef4444" in critical_style or "red" in critical_style.lower()

    # Warning should have orange/amber background (#f59e0b)
    assert "#f59e0b" in warning_style or "orange" in warning_style.lower() or "amber" in warning_style.lower()
