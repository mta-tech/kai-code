"""Ralph stop hook for intercepting agent exit and maintaining loops.

This module implements the core stop hook mechanism that enables Ralph Wiggum
autonomous loops. The hook intercepts agent exit attempts, checks completion
criteria, and re-feeds the prompt to continue the loop.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from kai_code.agent import KaiAgent, KaiResult
    from kai_code.ralph_loop import RalphLoopManager

from kai_code.ralph_logger import log_ralph_iteration, log_ralph_completion


class RalphStopHook:
    """Hook that intercepts agent exit to maintain Ralph loop.

    This hook is called when the agent completes a run. It checks if a Ralph
    loop is active and whether to continue or exit based on completion criteria
    and safety limits.

    Example:
        manager = RalphLoopManager(root_dir)
        hook = RalphStopHook(manager)

        result = agent.run(prompt)
        should_continue, next_prompt = hook.on_agent_complete(agent, result)

        if should_continue:
            result = agent.run(next_prompt)  # Loop continues
    """

    def __init__(self, manager: "RalphLoopManager"):
        """Initialize stop hook.

        Args:
            manager: RalphLoopManager instance to check loop state.
        """
        self.manager = manager

    def on_agent_complete(
        self,
        agent: "KaiAgent",
        result: "KaiResult"
    ) -> tuple[bool, str | None]:
        """Called when agent attempts to exit.

        This method determines whether the Ralph loop should continue or
        allow the agent to exit normally.

        Args:
            agent: KaiAgent instance that just completed.
            result: KaiResult from the agent's run.

        Returns:
            Tuple of (should_continue, next_prompt):
                - should_continue: True to re-feed prompt, False to exit
                - next_prompt: Prompt for next iteration (if should_continue)
        """
        # No active loop - allow normal exit
        if not self.manager.is_active():
            return (False, None)

        # Log output for debugging
        self.manager.log_output(result.output)

        # Extract token usage if available
        tokens_used = 0
        if hasattr(result, "raw") and isinstance(result.raw, dict):
            usage = result.raw.get("usage", {})
            if isinstance(usage, dict):
                tokens_used = usage.get("total_tokens", 0)

        # Check completion promise
        if self.manager.check_completion(result.output):
            state = self.manager.get_state()
            if state:
                log_ralph_completion("completion promise found", state)
            print("✓ Ralph loop completed: found completion promise")
            self.manager.cancel_loop()
            return (False, None)

        # Check token limit
        if tokens_used > 0:
            if not self.manager.update_token_usage(tokens_used):
                print("⚠ Ralph loop stopped: token limit exceeded")
                self.manager.cancel_loop()
                return (False, None)

        # Check other safety limits (max iterations, timeout)
        if not self.manager.should_continue():
            state = self.manager.get_state()
            if state and state.is_timed_out():
                print("⚠ Ralph loop stopped: timeout exceeded")
            elif state and state.max_iterations:
                print(f"⚠ Ralph loop stopped: max iterations ({state.max_iterations}) reached")
            self.manager.cancel_loop()
            return (False, None)

        # Continue loop - increment and re-feed
        self.manager.increment_iteration()
        state = self.manager.get_state()

        if state:
            iteration = state.current_iteration
            max_iter = state.max_iterations or "∞"
            tokens = state.total_tokens
            print(f"⟳ Ralph loop: iteration {iteration}/{max_iter} (tokens: {tokens:,})")

            # Log iteration progress
            log_ralph_iteration(iteration, state.max_iterations, tokens_used, tokens)

        return (True, self.manager.get_prompt())
