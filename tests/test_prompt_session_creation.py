"""Test prompt session creation without ValueError.

This test verifies the fix for the critical bug where @kb.add("s-enter")
caused a ValueError: Invalid key when creating the prompt session.
"""
import pytest

from kai_code.rich_config import SessionState
from kai_code.rich_input import create_prompt_session


def test_prompt_session_creates_without_error():
    """Test that prompt session can be created without ValueError.

    This is a regression test for the bug where @kb.add("s-enter")
    caused: RuntimeError: Invalid key 's-enter' when creating
    the PromptSession.

    The fix removes the invalid s-enter binding and uses c-j instead.
    """
    session_state = SessionState()

    # This should not raise ValueError or RuntimeError
    session = create_prompt_session("test-assistant", session_state)

    # Verify session was created
    assert session is not None
    # Verify it's a PromptSession
    from prompt_toolkit import PromptSession
    assert isinstance(session, PromptSession)


def test_prompt_session_with_optional_args():
    """Test prompt session creation with optional arguments."""
    session_state = SessionState(auto_approve=True)

    # Should work with all optional args
    session = create_prompt_session(
        "test-assistant",
        session_state,
        image_tracker=None,
        background_task_callback=None
    )

    assert session is not None
