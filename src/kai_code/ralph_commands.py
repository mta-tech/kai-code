"""Ralph Wiggum slash commands for TUI/CLI interaction.

This module provides slash commands for starting, monitoring, and canceling
Ralph autonomous loops. Commands integrate with the TUI and Rich UI systems.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from kai_code.agent import KaiAgent


def ralph_loop_command(
    agent: "KaiAgent",
    prompt: str,
    completion_promise: str | None = None,
    max_iterations: int | None = None,
    timeout_seconds: int | None = None,
    token_limit: int | None = 500_000,
) -> str:
    """Start a Ralph autonomous loop.

    Args:
        agent: KaiAgent instance.
        prompt: Task prompt to be re-fed each iteration.
        completion_promise: Exact string to detect completion (optional).
        max_iterations: Maximum iterations before stopping (default: 50).
        timeout_seconds: Wall-clock timeout in seconds (optional).
        token_limit: Maximum total tokens to use (default: 500K).

    Returns:
        Status message indicating loop started.

    Example:
        /ralph-loop "Fix all tests" --completion-promise TESTS_PASS --max-iterations 30
    """
    # Start the Ralph loop
    agent.ralph_manager.start_loop(
        prompt=prompt,
        completion_promise=completion_promise,
        max_iterations=max_iterations,
        timeout_seconds=timeout_seconds,
        token_limit=token_limit,
    )

    # Format status message
    max_iter = max_iterations or 50
    promise_msg = f" (completing on '{completion_promise}')" if completion_promise else ""
    timeout_msg = f", {timeout_seconds}s timeout" if timeout_seconds else ""
    token_msg = f", {token_limit:,} token limit" if token_limit else ""

    return f"⟳ Ralph loop started: max {max_iter} iterations{timeout_msg}{token_msg}{promise_msg}\n" \
           f"Task: {prompt}\n" \
           f"Loop will continue until completion promise found or limits reached."


def cancel_ralph_command(agent: "KaiAgent") -> str:
    """Cancel active Ralph loop.

    Args:
        agent: KaiAgent instance.

    Returns:
        Status message indicating loop canceled or not active.

    Example:
        /cancel-ralph
    """
    if not agent.ralph_manager.is_active():
        return "No active Ralph loop to cancel."

    state = agent.ralph_manager.get_state()
    iteration = state.current_iteration if state else 0
    tokens = state.total_tokens if state else 0

    agent.ralph_manager.cancel_loop()

    return f"✓ Ralph loop canceled at iteration {iteration} ({tokens:,} tokens used)."


def ralph_status_command(agent: "KaiAgent") -> str:
    """Show Ralph loop status.

    Args:
        agent: KaiAgent instance.

    Returns:
        Formatted status information.

    Example:
        /ralph-status
    """
    if not agent.ralph_manager.is_active():
        return "No active Ralph loop."

    state = agent.ralph_manager.get_state()
    if not state:
        return "Ralph loop state unavailable."

    # Format status information
    max_iter = state.max_iterations or "∞"
    elapsed_time = _format_elapsed(state.started_at)
    timeout_status = f" / {state.timeout_seconds}s" if state.timeout_seconds else ""
    token_pct = ""
    if state.token_limit:
        pct = (state.total_tokens / state.token_limit) * 100
        token_pct = f" ({pct:.1f}%)"

    status = f"""
⟳ Ralph Loop Status

Task: {state.prompt}
Completion Promise: {state.completion_promise or 'None'}

Progress:
  Iteration: {state.current_iteration} / {max_iter}
  Elapsed: {elapsed_time}{timeout_status}
  Tokens: {state.total_tokens:,}{token_pct}

Recent Output:
{_format_output_log(state.output_log)}
    """.strip()

    return status


def _format_elapsed(started_at: int) -> str:
    """Format elapsed time in human-readable format.

    Args:
        started_at: Unix timestamp when loop started.

    Returns:
        Formatted elapsed time (e.g., "5m 30s").
    """
    import time

    elapsed = int(time.time()) - started_at
    minutes = elapsed // 60
    seconds = elapsed % 60

    if minutes > 0:
        return f"{minutes}m {seconds}s"
    return f"{seconds}s"


def _format_output_log(output_log: list[str]) -> str:
    """Format output log for display.

    Args:
        output_log: List of recent output snippets.

    Returns:
        Formatted output log.
    """
    if not output_log:
        return "  (no output yet)"

    # Show last 3 outputs
    recent = output_log[-3:]
    formatted = []
    for i, output in enumerate(recent, 1):
        formatted.append(f"  [{len(output_log) - len(recent) + i}] {output}")

    return "\n".join(formatted)
