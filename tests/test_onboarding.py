"""Tests for the onboarding state management and integration flows."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

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


# =============================================================================
# Integration Tests: Startup Banner and Quick Start Panel
# =============================================================================


def test_startup_shows_quickstart_for_first_time_user(tmp_path: Path) -> None:
    """Test that first startup shows Quick Start panel for first-time users."""
    from kai_code.rich_config import SessionState

    fake_home = tmp_path / "home"
    fake_home.mkdir()

    with patch("kai_code.onboarding.Path.home", return_value=fake_home):
        with patch("kai_code.rich_main.is_first_time_user", return_value=True) as mock_first_time:
            with patch("kai_code.rich_main.render_quick_start_panel") as mock_render:
                with patch("kai_code.rich_main.mark_onboarding_complete") as mock_mark:
                    with patch("kai_code.rich_main.console"):
                        from kai_code.rich_main import _show_startup_banner

                        session_state = SessionState()
                        _show_startup_banner(session_state)

                        # Verify Quick Start panel was rendered
                        mock_render.assert_called_once()
                        # Verify onboarding was marked complete
                        mock_mark.assert_called_once()


def test_startup_does_not_show_quickstart_for_returning_user(tmp_path: Path) -> None:
    """Test that subsequent startups do not show Quick Start panel."""
    from kai_code.rich_config import SessionState

    fake_home = tmp_path / "home"
    fake_home.mkdir()
    kai_dir = fake_home / ".kai"
    kai_dir.mkdir()
    marker = kai_dir / ".onboarding_complete"
    marker.touch()

    with patch("kai_code.onboarding.Path.home", return_value=fake_home):
        with patch("kai_code.rich_main.is_first_time_user", return_value=False):
            with patch("kai_code.rich_main.render_quick_start_panel") as mock_render:
                with patch("kai_code.rich_main.console"):
                    from kai_code.rich_main import _show_startup_banner

                    session_state = SessionState()
                    _show_startup_banner(session_state)

                    # Verify Quick Start panel was NOT rendered
                    mock_render.assert_not_called()


def test_quickstart_command_renders_panel() -> None:
    """Test that /quickstart command shows the Quick Start panel."""
    from kai_code.rich_commands import handle_command

    agent = MagicMock()

    with patch("kai_code.rich_commands.render_quick_start_panel") as mock_render:
        with patch("kai_code.rich_commands.console"):
            result = handle_command("/quickstart", agent)

            # Command should return None (handled, not exit)
            assert result is None
            # Panel should be rendered
            mock_render.assert_called_once()


def test_show_quickstart_flag_forces_panel_display(tmp_path: Path) -> None:
    """Test that --show-quick-start flag forces Quick Start panel display."""
    from kai_code.rich_config import SessionState

    fake_home = tmp_path / "home"
    fake_home.mkdir()
    kai_dir = fake_home / ".kai"
    kai_dir.mkdir()
    marker = kai_dir / ".onboarding_complete"
    marker.touch()

    # Even with marker file present, the flag should force the panel to show
    with patch("kai_code.onboarding.Path.home", return_value=fake_home):
        with patch("kai_code.rich_main.is_first_time_user", return_value=False):
            with patch("kai_code.rich_main.render_quick_start_panel") as mock_render:
                with patch("kai_code.rich_main.console"):
                    from kai_code.rich_main import _show_startup_banner

                    # Create session state with show_quick_start=True
                    session_state = SessionState(show_quick_start=True)
                    _show_startup_banner(session_state)

                    # Verify Quick Start panel WAS rendered due to flag
                    mock_render.assert_called_once()


def test_no_splash_suppresses_quickstart(tmp_path: Path) -> None:
    """Test that --no-splash flag suppresses Quick Start panel."""
    from kai_code.rich_config import SessionState

    fake_home = tmp_path / "home"
    fake_home.mkdir()

    with patch("kai_code.onboarding.Path.home", return_value=fake_home):
        with patch("kai_code.rich_main.is_first_time_user", return_value=True):
            with patch("kai_code.rich_main.render_quick_start_panel") as mock_render:
                with patch("kai_code.rich_main.console") as mock_console:
                    from kai_code.rich_main import _show_startup_banner

                    # Create session state with no_splash=True
                    session_state = SessionState(no_splash=True)
                    _show_startup_banner(session_state)

                    # Verify Quick Start panel was NOT rendered
                    mock_render.assert_not_called()
                    # Verify nothing was printed (no_splash early return)
                    mock_console.print.assert_not_called()


def test_parse_args_show_quick_start_flag() -> None:
    """Test that --show-quick-start CLI flag is parsed correctly."""
    from kai_code.rich_main import parse_args

    # Without flag
    args = parse_args([])
    assert args.show_quick_start is False

    # With flag
    args = parse_args(["--show-quick-start"])
    assert args.show_quick_start is True


def test_parse_args_no_splash_flag() -> None:
    """Test that --no-splash CLI flag is parsed correctly."""
    from kai_code.rich_main import parse_args

    # Without flag
    args = parse_args([])
    assert args.no_splash is False

    # With flag
    args = parse_args(["--no-splash"])
    assert args.no_splash is True


def test_session_state_show_quick_start_default() -> None:
    """Test that SessionState defaults show_quick_start to False."""
    from kai_code.rich_config import SessionState

    session_state = SessionState()
    assert session_state.show_quick_start is False


def test_session_state_show_quick_start_set() -> None:
    """Test that SessionState can set show_quick_start to True."""
    from kai_code.rich_config import SessionState

    session_state = SessionState(show_quick_start=True)
    assert session_state.show_quick_start is True


def test_quickstart_marks_onboarding_complete_for_first_time_only(tmp_path: Path) -> None:
    """Test that onboarding is only marked complete for actual first-time users."""
    from kai_code.rich_config import SessionState

    fake_home = tmp_path / "home"
    fake_home.mkdir()
    kai_dir = fake_home / ".kai"
    kai_dir.mkdir()
    marker = kai_dir / ".onboarding_complete"
    marker.touch()

    # When using --show-quick-start flag (not first-time user), onboarding
    # should NOT be marked complete again
    with patch("kai_code.onboarding.Path.home", return_value=fake_home):
        with patch("kai_code.rich_main.is_first_time_user", return_value=False):
            with patch("kai_code.rich_main.render_quick_start_panel"):
                with patch("kai_code.rich_main.mark_onboarding_complete") as mock_mark:
                    with patch("kai_code.rich_main.console"):
                        from kai_code.rich_main import _show_startup_banner

                        session_state = SessionState(show_quick_start=True)
                        _show_startup_banner(session_state)

                        # mark_onboarding_complete should NOT be called
                        # because user is not first-time
                        mock_mark.assert_not_called()


def test_full_onboarding_flow(tmp_path: Path) -> None:
    """Integration test: full onboarding flow from first use to returning user."""
    fake_home = tmp_path / "home"
    fake_home.mkdir()

    with patch("kai_code.onboarding.Path.home", return_value=fake_home):
        # Step 1: First launch - user is first-time
        assert is_first_time_user() is True

        # Step 2: Mark onboarding complete (simulating what startup does)
        result = mark_onboarding_complete()
        assert result is True

        # Step 3: Second launch - user is no longer first-time
        assert is_first_time_user() is False

        # Step 4: User wants to see quick start again via reset
        result = reset_onboarding()
        assert result is True

        # Step 5: After reset, user is first-time again
        assert is_first_time_user() is True
