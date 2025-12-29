"""Ralph Wiggum progress logging and monitoring.

This module provides logging utilities for tracking Ralph loop progress,
iteration metrics, and completion status.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from kai_code.ralph_loop import RalphLoopState

logger = logging.getLogger(__name__)


def log_ralph_start(state: "RalphLoopState") -> None:
    """Log Ralph loop start.

    Args:
        state: Ralph loop state.
    """
    max_iter = state.max_iterations or "∞"
    logger.info(f"⟳ Ralph loop started: {state.prompt[:50]}...")
    logger.info(f"  Max iterations: {max_iter}")
    logger.info(f"  Completion promise: {state.completion_promise or 'None'}")
    logger.info(f"  Token limit: {state.token_limit:,}")
    if state.timeout_seconds:
        logger.info(f"  Timeout: {state.timeout_seconds}s")


def log_ralph_iteration(
    iteration: int,
    max_iterations: int | None,
    tokens_used: int,
    total_tokens: int,
) -> None:
    """Log Ralph loop iteration progress.

    Args:
        iteration: Current iteration number.
        max_iterations: Maximum iterations allowed.
        tokens_used: Tokens used in this iteration.
        total_tokens: Total tokens used so far.
    """
    max_iter = max_iterations or "∞"
    logger.info(f"⟳ Ralph iteration {iteration}/{max_iter}")
    logger.info(f"  Tokens this iteration: {tokens_used:,}")
    logger.info(f"  Total tokens: {total_tokens:,}")


def log_ralph_completion(reason: str, state: "RalphLoopState") -> None:
    """Log Ralph loop completion.

    Args:
        reason: Reason for completion.
        state: Final Ralph loop state.
    """
    logger.info(f"✓ Ralph loop completed: {reason}")
    logger.info(f"  Total iterations: {state.current_iteration}")
    logger.info(f"  Total tokens: {state.total_tokens:,}")


def log_ralph_error(error: Exception, state: "RalphLoopState") -> None:
    """Log Ralph loop error.

    Args:
        error: Exception that occurred.
        state: Ralph loop state when error occurred.
    """
    logger.error(f"✗ Ralph loop error: {error}")
    logger.error(f"  At iteration: {state.current_iteration}")
    logger.error(f"  Total tokens used: {state.total_tokens:,}")


def write_ralph_metrics(state: "RalphLoopState", root_dir: Path) -> None:
    """Write Ralph loop metrics to file.

    Args:
        state: Final Ralph loop state.
        root_dir: Project root directory.
    """
    import json
    import time

    metrics_file = root_dir / ".kai" / "ralph-metrics.json"
    metrics_file.parent.mkdir(parents=True, exist_ok=True)

    # Load existing metrics
    metrics = []
    if metrics_file.exists():
        try:
            metrics = json.loads(metrics_file.read_text())
        except Exception:
            pass

    # Append new metrics
    elapsed = int(time.time()) - state.started_at
    metrics.append({
        "timestamp": state.started_at,
        "elapsed_seconds": elapsed,
        "iterations": state.current_iteration,
        "total_tokens": state.total_tokens,
        "completion_promise": state.completion_promise,
        "max_iterations": state.max_iterations,
        "prompt": state.prompt[:100],  # Truncate prompt for logging
    })

    # Keep only last 50 runs
    metrics = metrics[-50:]

    # Write metrics
    metrics_file.write_text(json.dumps(metrics, indent=2))
