"""Tests for progress indicator configuration options.

Tests the configuration settings in rich_config.py that control
progress indicator behavior including:
- progress_enabled setting
- progress_file_size_threshold setting
- progress_update_interval_ms setting
- Environment variable support for all settings
"""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest


class TestProgressConfigDefaults:
    """Test default values for progress configuration."""

    def test_progress_enabled_default_true(self) -> None:
        """Default progress_enabled should be True."""
        from kai_code.rich_config import RichSettings

        settings = RichSettings(
            openai_api_key=None,
            anthropic_api_key=None,
            google_api_key=None,
            tavily_api_key=None,
            project_root=None,
        )
        assert settings.progress_enabled is True

    def test_progress_file_size_threshold_default_50kb(self) -> None:
        """Default progress_file_size_threshold should be 50KB (51200 bytes)."""
        from kai_code.rich_config import RichSettings

        settings = RichSettings(
            openai_api_key=None,
            anthropic_api_key=None,
            google_api_key=None,
            tavily_api_key=None,
            project_root=None,
        )
        assert settings.progress_file_size_threshold == 50 * 1024

    def test_progress_update_interval_default_100ms(self) -> None:
        """Default progress_update_interval_ms should be 100."""
        from kai_code.rich_config import RichSettings

        settings = RichSettings(
            openai_api_key=None,
            anthropic_api_key=None,
            google_api_key=None,
            tavily_api_key=None,
            project_root=None,
        )
        assert settings.progress_update_interval_ms == 100


class TestProgressConfigFromEnvironment:
    """Test progress configuration from environment variables."""

    def test_progress_enabled_from_env_false(self) -> None:
        """KAI_PROGRESS_ENABLED=false should disable progress."""
        from kai_code.rich_config import RichSettings

        with patch.dict(os.environ, {"KAI_PROGRESS_ENABLED": "false"}, clear=False):
            settings = RichSettings.from_environment()
            assert settings.progress_enabled is False

    def test_progress_enabled_from_env_zero(self) -> None:
        """KAI_PROGRESS_ENABLED=0 should disable progress."""
        from kai_code.rich_config import RichSettings

        with patch.dict(os.environ, {"KAI_PROGRESS_ENABLED": "0"}, clear=False):
            settings = RichSettings.from_environment()
            assert settings.progress_enabled is False

    def test_progress_enabled_from_env_no(self) -> None:
        """KAI_PROGRESS_ENABLED=no should disable progress."""
        from kai_code.rich_config import RichSettings

        with patch.dict(os.environ, {"KAI_PROGRESS_ENABLED": "no"}, clear=False):
            settings = RichSettings.from_environment()
            assert settings.progress_enabled is False

    def test_progress_enabled_from_env_off(self) -> None:
        """KAI_PROGRESS_ENABLED=off should disable progress."""
        from kai_code.rich_config import RichSettings

        with patch.dict(os.environ, {"KAI_PROGRESS_ENABLED": "OFF"}, clear=False):
            settings = RichSettings.from_environment()
            assert settings.progress_enabled is False

    def test_progress_enabled_from_env_case_insensitive(self) -> None:
        """KAI_PROGRESS_ENABLED should be case-insensitive."""
        from kai_code.rich_config import RichSettings

        with patch.dict(os.environ, {"KAI_PROGRESS_ENABLED": "FALSE"}, clear=False):
            settings = RichSettings.from_environment()
            assert settings.progress_enabled is False

    def test_progress_enabled_from_env_true(self) -> None:
        """KAI_PROGRESS_ENABLED=true should keep progress enabled (default)."""
        from kai_code.rich_config import RichSettings

        with patch.dict(os.environ, {"KAI_PROGRESS_ENABLED": "true"}, clear=False):
            settings = RichSettings.from_environment()
            assert settings.progress_enabled is True

    def test_progress_file_size_threshold_from_env(self) -> None:
        """KAI_PROGRESS_FILE_SIZE_THRESHOLD should override default threshold."""
        from kai_code.rich_config import RichSettings

        with patch.dict(os.environ, {"KAI_PROGRESS_FILE_SIZE_THRESHOLD": "100000"}, clear=False):
            settings = RichSettings.from_environment()
            assert settings.progress_file_size_threshold == 100000

    def test_progress_file_size_threshold_from_env_invalid(self) -> None:
        """Invalid KAI_PROGRESS_FILE_SIZE_THRESHOLD should keep default."""
        from kai_code.rich_config import RichSettings

        with patch.dict(os.environ, {"KAI_PROGRESS_FILE_SIZE_THRESHOLD": "not_a_number"}, clear=False):
            settings = RichSettings.from_environment()
            assert settings.progress_file_size_threshold == 50 * 1024

    def test_progress_update_interval_from_env(self) -> None:
        """KAI_PROGRESS_UPDATE_INTERVAL_MS should override default interval."""
        from kai_code.rich_config import RichSettings

        with patch.dict(os.environ, {"KAI_PROGRESS_UPDATE_INTERVAL_MS": "200"}, clear=False):
            settings = RichSettings.from_environment()
            assert settings.progress_update_interval_ms == 200

    def test_progress_update_interval_from_env_invalid(self) -> None:
        """Invalid KAI_PROGRESS_UPDATE_INTERVAL_MS should keep default."""
        from kai_code.rich_config import RichSettings

        with patch.dict(os.environ, {"KAI_PROGRESS_UPDATE_INTERVAL_MS": "not_a_number"}, clear=False):
            settings = RichSettings.from_environment()
            assert settings.progress_update_interval_ms == 100


class TestProgressConfigCustomValues:
    """Test creating RichSettings with custom progress values."""

    def test_custom_progress_enabled(self) -> None:
        """Should be able to create settings with progress_enabled=False."""
        from kai_code.rich_config import RichSettings

        settings = RichSettings(
            openai_api_key=None,
            anthropic_api_key=None,
            google_api_key=None,
            tavily_api_key=None,
            project_root=None,
            progress_enabled=False,
        )
        assert settings.progress_enabled is False

    def test_custom_progress_file_size_threshold(self) -> None:
        """Should be able to create settings with custom file size threshold."""
        from kai_code.rich_config import RichSettings

        settings = RichSettings(
            openai_api_key=None,
            anthropic_api_key=None,
            google_api_key=None,
            tavily_api_key=None,
            project_root=None,
            progress_file_size_threshold=100 * 1024,  # 100KB
        )
        assert settings.progress_file_size_threshold == 100 * 1024

    def test_custom_progress_update_interval(self) -> None:
        """Should be able to create settings with custom update interval."""
        from kai_code.rich_config import RichSettings

        settings = RichSettings(
            openai_api_key=None,
            anthropic_api_key=None,
            google_api_key=None,
            tavily_api_key=None,
            project_root=None,
            progress_update_interval_ms=500,
        )
        assert settings.progress_update_interval_ms == 500


class TestProgressDisabledBehavior:
    """Test that progress_enabled=False disables progress reporting."""

    def test_web_report_progress_respects_enabled_flag(self) -> None:
        """_report_progress in web.py should respect progress_enabled."""
        from kai_code.progress import ToolProgress, ProgressPhase, get_progress_manager, reset_progress_manager

        # Reset progress manager state
        reset_progress_manager()
        progress_manager = get_progress_manager()

        # Track reported progress
        reported = []
        progress_manager.set_callback(lambda p: reported.append(p))

        # Import _report_progress after setting up mock
        from kai_code.tools.web import _report_progress

        with patch("kai_code.tools.web.rich_settings") as mock_settings:
            # Test when enabled
            mock_settings.progress_enabled = True
            _report_progress(
                ToolProgress(
                    tool_name="test",
                    status_message="Test message",
                    phase=ProgressPhase.STARTING,
                )
            )
            assert len(reported) == 1

            # Test when disabled
            mock_settings.progress_enabled = False
            _report_progress(
                ToolProgress(
                    tool_name="test",
                    status_message="Should not appear",
                    phase=ProgressPhase.COMPLETE,
                )
            )
            # Should still be 1, not 2
            assert len(reported) == 1

        # Cleanup
        progress_manager.clear_callback()
        reset_progress_manager()


class TestGlobalRichSettings:
    """Test the global rich_settings instance."""

    def test_rich_settings_exists(self) -> None:
        """Global rich_settings should exist and have progress settings."""
        from kai_code.rich_config import rich_settings

        assert hasattr(rich_settings, "progress_enabled")
        assert hasattr(rich_settings, "progress_file_size_threshold")
        assert hasattr(rich_settings, "progress_update_interval_ms")

    def test_rich_settings_has_expected_types(self) -> None:
        """Global rich_settings progress values should have correct types."""
        from kai_code.rich_config import rich_settings

        assert isinstance(rich_settings.progress_enabled, bool)
        assert isinstance(rich_settings.progress_file_size_threshold, int)
        assert isinstance(rich_settings.progress_update_interval_ms, int)
