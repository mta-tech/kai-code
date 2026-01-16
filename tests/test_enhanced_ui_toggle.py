"""Test enhanced UI environment variable toggle."""
import os


def test_enhanced_ui_default():
    """Test enhanced UI defaults to True when env var not set."""
    # Remove env var if set
    os.environ.pop("KAI_ENHANCED_UI", None)

    from kai_code.rich_config import _parse_bool_env

    result = _parse_bool_env("KAI_ENHANCED_UI", default=True)
    assert result is True


def test_enhanced_ui_enabled():
    """Test enhanced UI can be enabled via env var."""
    os.environ["KAI_ENHANCED_UI"] = "1"

    from kai_code.rich_config import _parse_bool_env

    result = _parse_bool_env("KAI_ENHANCED_UI", default=False)
    assert result is True

    # Cleanup
    os.environ.pop("KAI_ENHANCED_UI", None)


def test_enhanced_ui_disabled():
    """Test enhanced UI can be disabled via env var."""
    os.environ["KAI_ENHANCED_UI"] = "0"

    from kai_code.rich_config import _parse_bool_env

    result = _parse_bool_env("KAI_ENHANCED_UI", default=True)
    assert result is False

    # Cleanup
    os.environ.pop("KAI_ENHANCED_UI", None)
