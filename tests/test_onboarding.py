"""Tests for the onboarding state management module."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from kai_code.onboarding import (
    get_kai_home_dir,
    is_first_time_user,
    mark_onboarding_complete,
    reset_onboarding,
)


def test_is_first_time_user_returns_true_when_marker_absent(tmp_path: Path) -> None:
    """Test that is_first_time_user() returns True when marker file doesn't exist."""
    fake_home = tmp_path / "home"
    fake_home.mkdir()

    with patch("kai_code.onboarding.Path.home", return_value=fake_home):
        # No marker file exists yet
        marker = fake_home / ".kai" / ".onboarding_complete"
        assert not marker.exists()
        assert is_first_time_user() is True


def test_is_first_time_user_returns_false_when_marker_exists(tmp_path: Path) -> None:
    """Test that is_first_time_user() returns False when marker file exists."""
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    kai_dir = fake_home / ".kai"
    kai_dir.mkdir()
    marker = kai_dir / ".onboarding_complete"
    marker.touch()

    with patch("kai_code.onboarding.Path.home", return_value=fake_home):
        assert marker.exists()
        assert is_first_time_user() is False


def test_mark_onboarding_complete_creates_marker(tmp_path: Path) -> None:
    """Test that mark_onboarding_complete() creates the marker file."""
    fake_home = tmp_path / "home"
    fake_home.mkdir()

    with patch("kai_code.onboarding.Path.home", return_value=fake_home):
        marker = fake_home / ".kai" / ".onboarding_complete"
        assert not marker.exists()

        result = mark_onboarding_complete()

        assert result is True
        assert marker.exists()


def test_mark_onboarding_complete_creates_kai_directory(tmp_path: Path) -> None:
    """Test that mark_onboarding_complete() creates ~/.kai/ if it doesn't exist."""
    fake_home = tmp_path / "home"
    fake_home.mkdir()

    with patch("kai_code.onboarding.Path.home", return_value=fake_home):
        kai_dir = fake_home / ".kai"
        assert not kai_dir.exists()

        mark_onboarding_complete()

        assert kai_dir.exists()
        assert kai_dir.is_dir()


def test_is_first_time_user_returns_false_after_mark_complete(tmp_path: Path) -> None:
    """Test that is_first_time_user() returns False after mark_onboarding_complete()."""
    fake_home = tmp_path / "home"
    fake_home.mkdir()

    with patch("kai_code.onboarding.Path.home", return_value=fake_home):
        # Initially a first-time user
        assert is_first_time_user() is True

        # Mark onboarding complete
        mark_onboarding_complete()

        # No longer a first-time user
        assert is_first_time_user() is False


def test_reset_onboarding_removes_marker(tmp_path: Path) -> None:
    """Test that reset_onboarding() removes the marker file."""
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    kai_dir = fake_home / ".kai"
    kai_dir.mkdir()
    marker = kai_dir / ".onboarding_complete"
    marker.touch()

    with patch("kai_code.onboarding.Path.home", return_value=fake_home):
        assert marker.exists()

        result = reset_onboarding()

        assert result is True
        assert not marker.exists()


def test_reset_onboarding_succeeds_when_no_marker(tmp_path: Path) -> None:
    """Test that reset_onboarding() returns True even when marker doesn't exist."""
    fake_home = tmp_path / "home"
    fake_home.mkdir()

    with patch("kai_code.onboarding.Path.home", return_value=fake_home):
        marker = fake_home / ".kai" / ".onboarding_complete"
        assert not marker.exists()

        result = reset_onboarding()

        assert result is True


def test_reset_onboarding_allows_reshowing_quickstart(tmp_path: Path) -> None:
    """Test that reset_onboarding() allows the quick start panel to show again."""
    fake_home = tmp_path / "home"
    fake_home.mkdir()

    with patch("kai_code.onboarding.Path.home", return_value=fake_home):
        # Mark onboarding complete
        mark_onboarding_complete()
        assert is_first_time_user() is False

        # Reset onboarding
        reset_onboarding()

        # Now we're a first-time user again
        assert is_first_time_user() is True


def test_get_kai_home_dir_returns_correct_path() -> None:
    """Test that get_kai_home_dir() returns the expected ~/.kai/ path."""
    expected = Path.home() / ".kai"
    assert get_kai_home_dir() == expected


def test_is_first_time_user_handles_permission_error(tmp_path: Path) -> None:
    """Test that is_first_time_user() returns False on permission error."""
    with patch("kai_code.onboarding._onboarding_marker_path") as mock_marker:
        mock_marker.return_value.exists.side_effect = PermissionError("Access denied")

        # Should return False (assume not first-time) to avoid disruption
        assert is_first_time_user() is False


def test_mark_onboarding_complete_handles_permission_error(tmp_path: Path) -> None:
    """Test that mark_onboarding_complete() returns False on permission error."""
    fake_home = tmp_path / "home"
    fake_home.mkdir()

    with patch("kai_code.onboarding.Path.home", return_value=fake_home):
        with patch("pathlib.Path.mkdir", side_effect=PermissionError("Access denied")):
            result = mark_onboarding_complete()
            assert result is False


def test_reset_onboarding_handles_permission_error(tmp_path: Path) -> None:
    """Test that reset_onboarding() returns False on permission error."""
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    kai_dir = fake_home / ".kai"
    kai_dir.mkdir()
    marker = kai_dir / ".onboarding_complete"
    marker.touch()

    with patch("kai_code.onboarding.Path.home", return_value=fake_home):
        with patch.object(Path, "unlink", side_effect=PermissionError("Access denied")):
            result = reset_onboarding()
            assert result is False
