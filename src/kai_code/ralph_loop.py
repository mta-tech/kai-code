"""Ralph loop state management and lifecycle control.

This module implements the core Ralph Wiggum technique for autonomous agent loops.
Ralph enables agents to work continuously on tasks until completion without human
intervention through a stop hook that intercepts exit and re-feeds the prompt.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any


@dataclass
class RalphLoopState:
    """Persistent state for Ralph loop.

    This dataclass tracks all state for an active Ralph loop, including
    iteration count, completion criteria, safety limits, and metrics.
    """

    active: bool = False
    prompt: str = ""
    completion_promise: str | None = None
    max_iterations: int | None = None
    current_iteration: int = 0
    started_at: int = 0  # Unix timestamp
    timeout_seconds: int | None = None
    token_limit: int | None = 500_000  # Default 500K tokens
    total_tokens: int = 0
    output_log: list[str] = field(default_factory=list)

    def is_timed_out(self) -> bool:
        """Check if wall-clock timeout has been exceeded.

        Returns:
            True if timeout_seconds is set and elapsed time exceeds it.
        """
        if self.timeout_seconds is None:
            return False
        elapsed = int(time.time()) - self.started_at
        return elapsed > self.timeout_seconds

    def check_token_limit(self, tokens_used: int) -> bool:
        """Update token count and check if limit exceeded.

        Args:
            tokens_used: Number of tokens used in this iteration.

        Returns:
            True if under limit, False if limit exceeded.
        """
        self.total_tokens += tokens_used
        if self.token_limit and self.total_tokens > self.token_limit:
            return False  # Stop loop
        return True

    def to_dict(self) -> dict[str, Any]:
        """Convert state to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RalphLoopState":
        """Create state from dictionary loaded from JSON.

        Args:
            data: Dictionary representation of state.

        Returns:
            RalphLoopState instance.
        """
        # Handle default factory fields
        if "output_log" not in data:
            data["output_log"] = []
        return cls(**data)


class RalphLoopManager:
    """Manages Ralph loop lifecycle and state.

    This class handles starting/stopping Ralph loops, checking completion
    criteria, enforcing safety limits, and persisting state to disk.

    Example:
        manager = RalphLoopManager(Path("/project"))
        manager.start_loop(
            prompt="Fix all tests",
            completion_promise="TESTS_PASS",
            max_iterations=30
        )

        while manager.is_active():
            result = agent.run(manager.get_prompt())
            if manager.check_completion(result.output):
                break
            manager.increment_iteration()
    """

    def __init__(self, root_dir: Path):
        """Initialize Ralph loop manager.

        Args:
            root_dir: Project root directory where .kai/ will be created.
        """
        self.root_dir = Path(root_dir).resolve()
        self.state_path = self.root_dir / ".kai" / "ralph-loop.json"
        self._state: RalphLoopState | None = None
        self._load_state()

    def _load_state(self) -> None:
        """Load state from disk if it exists."""
        if self.state_path.exists():
            try:
                data = json.loads(self.state_path.read_text())
                self._state = RalphLoopState.from_dict(data)
            except Exception:
                # Corrupted state file, start fresh
                self._state = None

    def _save_state(self) -> None:
        """Persist current state to disk."""
        if self._state is None:
            return

        # Ensure .kai directory exists
        self.state_path.parent.mkdir(parents=True, exist_ok=True)

        # Write state atomically
        self.state_path.write_text(
            json.dumps(self._state.to_dict(), indent=2)
        )

    def start_loop(
        self,
        prompt: str,
        completion_promise: str | None = None,
        max_iterations: int | None = None,
        timeout_seconds: int | None = None,
        token_limit: int | None = 500_000,
    ) -> None:
        """Activate Ralph loop with given parameters.

        Args:
            prompt: Task prompt to be re-fed each iteration.
            completion_promise: Exact string to detect completion (optional).
            max_iterations: Maximum iterations before stopping (default: 50).
            timeout_seconds: Wall-clock timeout in seconds (optional).
            token_limit: Maximum total tokens to use (default: 500K).
        """
        self._state = RalphLoopState(
            active=True,
            prompt=prompt,
            completion_promise=completion_promise,
            max_iterations=max_iterations or 50,
            current_iteration=0,
            started_at=int(time.time()),
            timeout_seconds=timeout_seconds,
            token_limit=token_limit,
            total_tokens=0,
            output_log=[],
        )
        self._save_state()

    def is_active(self) -> bool:
        """Check if Ralph loop is currently active.

        Returns:
            True if loop is active, False otherwise.
        """
        return self._state is not None and self._state.active

    def check_completion(self, output: str) -> bool:
        """Check if completion promise appears in agent output.

        Args:
            output: Agent output text to check.

        Returns:
            True if completion promise found, False otherwise.
        """
        if self._state is None or self._state.completion_promise is None:
            return False
        return self._state.completion_promise in output

    def should_continue(self) -> bool:
        """Determine if loop should continue based on limits.

        Checks max iterations, timeout, and other safety limits.

        Returns:
            True if loop should continue, False if limits reached.
        """
        if self._state is None:
            return False

        # Check max iterations
        if self._state.max_iterations is not None:
            if self._state.current_iteration >= self._state.max_iterations:
                return False

        # Check timeout
        if self._state.is_timed_out():
            return False

        return True

    def increment_iteration(self) -> None:
        """Increment iteration counter and save state."""
        if self._state is not None:
            self._state.current_iteration += 1
            self._save_state()

    def get_prompt(self) -> str:
        """Get current prompt for re-feeding.

        Returns:
            The prompt string, or empty string if no active loop.
        """
        return self._state.prompt if self._state else ""

    def get_state(self) -> RalphLoopState | None:
        """Get current loop state.

        Returns:
            Current RalphLoopState or None if no active loop.
        """
        return self._state

    def cancel_loop(self) -> None:
        """Deactivate Ralph loop."""
        if self._state is not None:
            self._state.active = False
            self._save_state()

    def log_output(self, output: str, max_length: int = 200) -> None:
        """Log agent output (truncated) for debugging.

        Args:
            output: Agent output text.
            max_length: Maximum length to store (default: 200 chars).
        """
        if self._state is not None:
            truncated = output[:max_length] + "..." if len(output) > max_length else output
            self._state.output_log.append(truncated)
            # Keep only last 10 outputs to avoid memory bloat
            if len(self._state.output_log) > 10:
                self._state.output_log = self._state.output_log[-10:]
            self._save_state()

    def update_token_usage(self, tokens_used: int) -> bool:
        """Update token count and check limit.

        Args:
            tokens_used: Tokens used in this iteration.

        Returns:
            True if under limit, False if limit exceeded.
        """
        if self._state is None:
            return True
        return self._state.check_token_limit(tokens_used)
