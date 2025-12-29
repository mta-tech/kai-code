"""End-to-end tests for Ralph Wiggum autonomous loop system."""

import json
import time
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from src.kai_code.agent import KaiAgent, KaiResult
from src.kai_code.ralph_loop import RalphLoopManager


@pytest.fixture
def temp_project(tmp_path):
    """Create a temporary project directory."""
    project = tmp_path / "test_project"
    project.mkdir()
    return project


@pytest.fixture
def mock_agent(temp_project):
    """Create a mock KaiAgent for testing."""
    # Create minimal agent without requiring actual LLM
    with patch('src.kai_code.agent.create_deep_agent'):
        agent = KaiAgent(
            root_dir=temp_project,
            model="mock-model",
            yolo=True,
        )
    return agent


class TestRalphE2E:
    """End-to-end tests for Ralph loop system."""

    def test_ralph_loop_completes_on_promise(self, mock_agent):
        """Test that Ralph loop completes when completion promise is found."""
        # Start Ralph loop
        mock_agent.ralph_manager.start_loop(
            prompt="Test task",
            completion_promise="TASK_COMPLETE",
            max_iterations=10,
        )

        # Verify loop is active
        assert mock_agent.ralph_manager.is_active() is True

        # Simulate agent completion with promise
        result = KaiResult(
            output="Work done. TASK_COMPLETE",
            messages=[],
            raw={},
        )

        # Check stop hook
        should_continue, next_prompt = mock_agent._ralph_hook.on_agent_complete(
            mock_agent, result
        )

        # Loop should stop
        assert should_continue is False
        assert next_prompt is None
        assert mock_agent.ralph_manager.is_active() is False

    def test_ralph_loop_stops_at_max_iterations(self, mock_agent):
        """Test that Ralph loop stops at max iterations."""
        # Start Ralph loop with low iteration limit
        mock_agent.ralph_manager.start_loop(
            prompt="Test task",
            max_iterations=3,
        )

        # Simulate iterations without completion promise
        # The loop stops AFTER reaching max_iterations, not at it
        for i in range(4):
            result = KaiResult(
                output=f"Iteration {i} output",
                messages=[],
                raw={"usage": {"total_tokens": 100}},
            )

            should_continue, next_prompt = mock_agent._ralph_hook.on_agent_complete(
                mock_agent, result
            )

            if i < 3:
                # Should continue for first 3 iterations (0, 1, 2)
                assert should_continue is True
                assert next_prompt == "Test task"
            else:
                # Should stop after iteration 3 (when current_iteration >= max)
                assert should_continue is False

    def test_ralph_loop_stops_at_token_limit(self, mock_agent):
        """Test that Ralph loop stops when token limit exceeded."""
        # Start Ralph loop with low token limit
        mock_agent.ralph_manager.start_loop(
            prompt="Test task",
            token_limit=500,
            max_iterations=10,
        )

        # Simulate iteration that exceeds token limit
        result = KaiResult(
            output="Output",
            messages=[],
            raw={"usage": {"total_tokens": 600}},
        )

        should_continue, next_prompt = mock_agent._ralph_hook.on_agent_complete(
            mock_agent, result
        )

        # Loop should stop due to token limit
        assert should_continue is False
        assert mock_agent.ralph_manager.is_active() is False

    def test_ralph_loop_state_persistence(self, temp_project):
        """Test that Ralph loop state persists across agent instances."""
        # Create first agent and start loop
        with patch('src.kai_code.agent.create_deep_agent'):
            agent1 = KaiAgent(root_dir=temp_project, model="mock", yolo=True)
            agent1.ralph_manager.start_loop(
                prompt="Persistent task",
                completion_promise="DONE",
                max_iterations=50,
            )
            # Increment iteration which saves state
            agent1.ralph_manager.increment_iteration()
            # Update token usage - need to do this before incrementing for it to persist
            agent1.ralph_manager._state.total_tokens = 100
            agent1.ralph_manager._save_state()

        # Create second agent - should load persisted state
        with patch('src.kai_code.agent.create_deep_agent'):
            agent2 = KaiAgent(root_dir=temp_project, model="mock", yolo=True)

        # Verify state was loaded
        assert agent2.ralph_manager.is_active() is True
        state = agent2.ralph_manager.get_state()
        assert state.prompt == "Persistent task"
        assert state.completion_promise == "DONE"
        assert state.current_iteration == 1
        assert state.total_tokens == 100

    def test_ralph_loop_incremental_iterations(self, mock_agent):
        """Test Ralph loop through multiple iterations."""
        # Start loop
        mock_agent.ralph_manager.start_loop(
            prompt="Multi-iteration task",
            completion_promise="ALL_DONE",
            max_iterations=5,
        )

        iterations_completed = 0

        # Simulate 3 iterations without completion
        for i in range(3):
            result = KaiResult(
                output=f"Progress update {i}",
                messages=[],
                raw={"usage": {"total_tokens": 50}},
            )

            should_continue, next_prompt = mock_agent._ralph_hook.on_agent_complete(
                mock_agent, result
            )

            assert should_continue is True
            assert next_prompt == "Multi-iteration task"
            iterations_completed += 1

        # Final iteration with completion promise
        result = KaiResult(
            output="Task finished. ALL_DONE",
            messages=[],
            raw={"usage": {"total_tokens": 50}},
        )

        should_continue, next_prompt = mock_agent._ralph_hook.on_agent_complete(
            mock_agent, result
        )

        assert should_continue is False
        assert iterations_completed == 3

        state = mock_agent.ralph_manager.get_state()
        assert state.current_iteration == 3
        # 3 iterations * 50 tokens = 150 total
        # The completion check happens before token update on the 4th call
        assert state.total_tokens == 150

    def test_ralph_loop_cancel(self, mock_agent):
        """Test canceling an active Ralph loop."""
        # Start loop
        mock_agent.ralph_manager.start_loop(
            prompt="Cancellable task",
            max_iterations=100,
        )

        assert mock_agent.ralph_manager.is_active() is True

        # Cancel loop
        mock_agent.ralph_manager.cancel_loop()

        assert mock_agent.ralph_manager.is_active() is False

        # Next iteration should not continue
        result = KaiResult(output="Output", messages=[], raw={})
        should_continue, _ = mock_agent._ralph_hook.on_agent_complete(
            mock_agent, result
        )

        assert should_continue is False

    def test_ralph_loop_output_logging(self, mock_agent):
        """Test that Ralph loop logs agent output."""
        mock_agent.ralph_manager.start_loop(
            prompt="Logged task",
            max_iterations=5,
        )

        # Simulate iterations with output
        for i in range(3):
            result = KaiResult(
                output=f"Detailed output for iteration {i}",
                messages=[],
                raw={"usage": {"total_tokens": 10}},
            )

            mock_agent._ralph_hook.on_agent_complete(mock_agent, result)

        # Verify output was logged
        state = mock_agent.ralph_manager.get_state()
        assert len(state.output_log) == 3
        assert "iteration 0" in state.output_log[0]
        assert "iteration 2" in state.output_log[2]


class TestRalphCLIIntegration:
    """Test Ralph integration with CLI flags."""

    def test_cli_starts_ralph_loop(self, temp_project):
        """Test that CLI --ralph flag starts Ralph loop."""
        # This test would require actual CLI integration
        # For now, verify manager can be started programmatically
        manager = RalphLoopManager(temp_project)
        manager.start_loop(
            prompt="CLI task",
            completion_promise="CLI_DONE",
            max_iterations=30,
            token_limit=500_000,
        )

        assert manager.is_active() is True
        assert manager.get_prompt() == "CLI task"

        state = manager.get_state()
        assert state.max_iterations == 30
        assert state.token_limit == 500_000


class TestRalphDbtPatterns:
    """Test dbt Ralph patterns."""

    def test_dbt_pattern_structure(self):
        """Test that dbt Ralph patterns are properly configured."""
        from src.kai_code.agents.dbt.ralph_patterns import DBT_RALPH_PATTERNS

        # Verify patterns exist
        assert "test-until-pass" in DBT_RALPH_PATTERNS
        assert "build-models" in DBT_RALPH_PATTERNS
        assert "lint-fix" in DBT_RALPH_PATTERNS

        # Verify pattern structure
        pattern = DBT_RALPH_PATTERNS["test-until-pass"]
        assert pattern.name == "test-until-pass"
        assert pattern.prompt is not None
        assert pattern.completion_promise == "TESTS_PASS"
        assert pattern.max_iterations > 0

    def test_list_dbt_patterns(self):
        """Test listing dbt Ralph patterns."""
        from src.kai_code.agents.dbt.ralph_patterns import list_dbt_ralph_patterns

        output = list_dbt_ralph_patterns()

        assert "test-until-pass" in output
        assert "build-models" in output
        assert "Available dbt Ralph patterns" in output


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
