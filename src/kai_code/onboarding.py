"""Onboarding state management for first-time user detection.

This module provides functions to detect first-time users and persist
onboarding state so the quick start panel only shows once by default.
"""
from __future__ import annotations

from pathlib import Path


def _onboarding_marker_path() -> Path:
    """Return the path to the onboarding completion marker file."""
    return Path.home() / ".kai" / ".onboarding_complete"


def is_first_time_user() -> bool:
    """Check if this is a first-time user.

    Returns True if the user has not completed onboarding (marker file
    does not exist), False otherwise.
    """
    try:
        return not _onboarding_marker_path().exists()
    except (OSError, PermissionError):
        # If we can't check, assume not first-time to avoid disruption
        return False


def mark_onboarding_complete() -> bool:
    """Mark onboarding as complete by creating the marker file.

    Creates the ~/.kai/ directory if it doesn't exist.

    Returns True on success, False on failure.
    """
    marker = _onboarding_marker_path()
    try:
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.touch()
        return True
    except (OSError, PermissionError):
        # Silently fail - onboarding will show again next time
        return False


def reset_onboarding() -> bool:
    """Reset onboarding state by removing the marker file.

    This allows the quick start panel to show again on next launch.
    Useful for testing or if the user wants to re-see the onboarding.

    Returns True on success or if marker didn't exist, False on failure.
    """
    marker = _onboarding_marker_path()
    try:
        if marker.exists():
            marker.unlink()
        return True
    except (OSError, PermissionError):
        return False


def get_kai_home_dir() -> Path:
    """Return the ~/.kai/ directory path.

    This is exposed for other modules that may need to reference
    the kai home directory.
    """
    return Path.home() / ".kai"
