"""Unit tests for Ralph Wiggum loop system."""

import json
import time
from pathlib import Path

import pytest

from src.kai_code.ralph_loop import RalphLoopManager, RalphLoopState


@pytest.fixture
def temp_project(tmp_path):
    """Create a temporary project directory."""
    return tmp_path


@pytest.fixture
def ralph_manager(temp_project):
    """Create a RalphLoopManager instance."""
    return RalphLoopManager(temp_project)


class TestRalphLoopState:
    """Tests for RalphLoopState dataclass."""

    def test_state_creation(self):
        """Test creating a RalphLoopState."""
        state = RalphLoopState(
            active=True,
            prompt="Fix all tests",
            completion_promise="TESTS_PASS",
            max_iterations=30,
            started_at=int(time.time()),
            token_limit=500_000,
        )

        assert state.active is True
        assert state.prompt == "Fix all tests"
        assert state.completion_promise == "TESTS_PASS"
        assert state.max_iterations == 30
        assert state.token_limit == 500_000

    def test_is_timed_out_no_timeout(self):
        """Test timeout check when no timeout is set."""
        state = RalphLoopState(
            started_at=int(time.time()),
            timeout_seconds=None,
        )
        assert state.is_timed_out() is False

    def test_is_timed_out_not_exceeded(self):
        """Test timeout check when timeout not exceeded."""
        state = RalphLoopState(
            started_at=int(time.time()),
            timeout_seconds=60,
        )
        assert state.is_timed_out() is False

    def test_is_timed_out_exceeded(self):
        """Test timeout check when timeout exceeded."""
        state = RalphLoopState(
            started_at=int(time.time()) - 120,  # 2 minutes ago
            timeout_seconds=60,  # 1 minute timeout
        )
        assert state.is_timed_out() is True

    def test_check_token_limit_under_limit(self):
        """Test token limit check under limit."""
        state = RalphLoopState(token_limit=1000)
        assert state.check_token_limit(500) is True
        assert state.total_tokens == 500

    def test_check_token_limit_at_limit(self):
        """Test token limit check at limit."""
        state = RalphLoopState(token_limit=1000)
        state.total_tokens = 999
        assert state.check_token_limit(1) is True
        assert state.total_tokens == 1000

    def test_check_token_limit_over_limit(self):
        """Test token limit check over limit."""
        state = RalphLoopState(token_limit=1000)
        state.total_tokens = 999
        assert state.check_token_limit(2) is False
        assert state.total_tokens == 1001

    def test_to_dict(self):
        """Test converting state to dict."""
        state = RalphLoopState(
            active=True,
            prompt="Fix tests",
            completion_promise="DONE",
        )
        data = state.to_dict()

        assert isinstance(data, dict)
        assert data["active"] is True
        assert data["prompt"] == "Fix tests"
        assert data["completion_promise"] == "DONE"

    def test_from_dict(self):
        """Test creating state from dict."""
        data = {
            "active": True,
            "prompt": "Fix tests",
            "completion_promise": "DONE",
            "max_iterations": 50,
            "current_iteration": 5,
            "started_at": int(time.time()),
            "timeout_seconds": None,
            "token_limit": 500_000,
            "total_tokens": 1000,
            "output_log": ["output1", "output2"],
        }
        state = RalphLoopState.from_dict(data)

        assert state.active is True
        assert state.prompt == "Fix tests"
        assert state.completion_promise == "DONE"
        assert state.max_iterations == 50
        assert state.current_iteration == 5
        assert state.total_tokens == 1000
        assert len(state.output_log) == 2


class TestRalphLoopManager:
    """Tests for RalphLoopManager."""

    def test_manager_init(self, ralph_manager, temp_project):
        """Test RalphLoopManager initialization."""
        assert ralph_manager.root_dir == temp_project
        assert ralph_manager.state_path == temp_project / ".kai" / "ralph-loop.json"
        assert ralph_manager._state is None

    def test_start_loop(self, ralph_manager):
        """Test starting a Ralph loop."""
        ralph_manager.start_loop(
            prompt="Fix all tests",
            completion_promise="TESTS_PASS",
            max_iterations=30,
        )

        assert ralph_manager.is_active() is True
        state = ralph_manager.get_state()
        assert state is not None
        assert state.prompt == "Fix all tests"
        assert state.completion_promise == "TESTS_PASS"
        assert state.max_iterations == 30
        assert state.current_iteration == 0

    def test_start_loop_defaults(self, ralph_manager):
        """Test starting a loop with default values."""
        ralph_manager.start_loop(prompt="Fix tests")

        state = ralph_manager.get_state()
        assert state is not None
        assert state.max_iterations == 50  # Default
        assert state.token_limit == 500_000  # Default

    def test_start_loop_persists_state(self, ralph_manager):
        """Test that starting a loop persists state to disk."""
        ralph_manager.start_loop(prompt="Fix tests")

        assert ralph_manager.state_path.exists()
        data = json.loads(ralph_manager.state_path.read_text())
        assert data["active"] is True
        assert data["prompt"] == "Fix tests"

    def test_is_active_when_not_started(self, ralph_manager):
        """Test is_active when loop not started."""
        assert ralph_manager.is_active() is False

    def test_is_active_when_started(self, ralph_manager):
        """Test is_active when loop started."""
        ralph_manager.start_loop(prompt="Fix tests")
        assert ralph_manager.is_active() is True

    def test_check_completion_no_promise(self, ralph_manager):
        """Test completion check with no promise set."""
        ralph_manager.start_loop(prompt="Fix tests")
        assert ralph_manager.check_completion("TESTS_PASS") is False

    def test_check_completion_promise_found(self, ralph_manager):
        """Test completion check when promise found."""
        ralph_manager.start_loop(
            prompt="Fix tests",
            completion_promise="TESTS_PASS"
        )
        assert ralph_manager.check_completion("All tests passed! TESTS_PASS") is True

    def test_check_completion_promise_not_found(self, ralph_manager):
        """Test completion check when promise not found."""
        ralph_manager.start_loop(
            prompt="Fix tests",
            completion_promise="TESTS_PASS"
        )
        assert ralph_manager.check_completion("Some tests failed") is False

    def test_should_continue_not_started(self, ralph_manager):
        """Test should_continue when loop not started."""
        assert ralph_manager.should_continue() is False

    def test_should_continue_under_limits(self, ralph_manager):
        """Test should_continue under limits."""
        ralph_manager.start_loop(
            prompt="Fix tests",
            max_iterations=50
        )
        assert ralph_manager.should_continue() is True

    def test_should_continue_at_max_iterations(self, ralph_manager):
        """Test should_continue at max iterations."""
        ralph_manager.start_loop(
            prompt="Fix tests",
            max_iterations=5
        )
        ralph_manager._state.current_iteration = 5
        assert ralph_manager.should_continue() is False

    def test_should_continue_timeout_exceeded(self, ralph_manager):
        """Test should_continue when timeout exceeded."""
        ralph_manager.start_loop(
            prompt="Fix tests",
            timeout_seconds=1
        )
        time.sleep(2)
        assert ralph_manager.should_continue() is False

    def test_increment_iteration(self, ralph_manager):
        """Test incrementing iteration counter."""
        ralph_manager.start_loop(prompt="Fix tests")
        assert ralph_manager._state.current_iteration == 0

        ralph_manager.increment_iteration()
        assert ralph_manager._state.current_iteration == 1

        ralph_manager.increment_iteration()
        assert ralph_manager._state.current_iteration == 2

    def test_get_prompt(self, ralph_manager):
        """Test getting prompt."""
        ralph_manager.start_loop(prompt="Fix all tests")
        assert ralph_manager.get_prompt() == "Fix all tests"

    def test_get_prompt_no_loop(self, ralph_manager):
        """Test getting prompt when no loop active."""
        assert ralph_manager.get_prompt() == ""

    def test_cancel_loop(self, ralph_manager):
        """Test canceling a loop."""
        ralph_manager.start_loop(prompt="Fix tests")
        assert ralph_manager.is_active() is True

        ralph_manager.cancel_loop()
        assert ralph_manager.is_active() is False

    def test_log_output(self, ralph_manager):
        """Test logging output."""
        ralph_manager.start_loop(prompt="Fix tests")
        ralph_manager.log_output("First output")
        ralph_manager.log_output("Second output")

        state = ralph_manager.get_state()
        assert len(state.output_log) == 2
        assert "First output" in state.output_log[0]
        assert "Second output" in state.output_log[1]

    def test_log_output_truncation(self, ralph_manager):
        """Test that long output is truncated."""
        ralph_manager.start_loop(prompt="Fix tests")
        long_output = "A" * 500
        ralph_manager.log_output(long_output, max_length=200)

        state = ralph_manager.get_state()
        assert len(state.output_log[0]) <= 204  # 200 + "..."

    def test_log_output_keeps_last_10(self, ralph_manager):
        """Test that only last 10 outputs are kept."""
        ralph_manager.start_loop(prompt="Fix tests")
        for i in range(15):
            ralph_manager.log_output(f"Output {i}")

        state = ralph_manager.get_state()
        assert len(state.output_log) == 10

    def test_update_token_usage_under_limit(self, ralph_manager):
        """Test updating token usage under limit."""
        ralph_manager.start_loop(
            prompt="Fix tests",
            token_limit=1000
        )
        assert ralph_manager.update_token_usage(500) is True
        assert ralph_manager._state.total_tokens == 500

    def test_update_token_usage_over_limit(self, ralph_manager):
        """Test updating token usage over limit."""
        ralph_manager.start_loop(
            prompt="Fix tests",
            token_limit=1000
        )
        ralph_manager._state.total_tokens = 999
        assert ralph_manager.update_token_usage(2) is False
        assert ralph_manager._state.total_tokens == 1001

    def test_state_persistence(self, ralph_manager, temp_project):
        """Test that state persists across manager instances."""
        # Start loop and modify state
        ralph_manager.start_loop(
            prompt="Fix tests",
            completion_promise="TESTS_PASS",
            max_iterations=30
        )
        ralph_manager.increment_iteration()
        ralph_manager.increment_iteration()

        # Create new manager and verify state loaded
        new_manager = RalphLoopManager(temp_project)
        assert new_manager.is_active() is True
        state = new_manager.get_state()
        assert state.prompt == "Fix tests"
        assert state.completion_promise == "TESTS_PASS"
        assert state.current_iteration == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
