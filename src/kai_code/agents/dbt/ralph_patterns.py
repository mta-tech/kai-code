"""Pre-configured Ralph Wiggum patterns for dbt workflows.

This module provides ready-to-use Ralph loop configurations optimized for
common dbt development tasks like testing, building, and linting.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from kai_code.agents.dbt.agent import DbtAgent


@dataclass
class RalphPattern:
    """A pre-configured Ralph loop pattern."""

    name: str
    description: str
    prompt: str
    completion_promise: str
    max_iterations: int
    timeout_seconds: int | None = None
    token_limit: int = 500_000


# Pre-configured dbt patterns
DBT_RALPH_PATTERNS = {
    "test-until-pass": RalphPattern(
        name="test-until-pass",
        description="Run dbt tests iteratively until all pass",
        prompt="Run 'dbt test' and fix any failures. Continue until all tests pass. Output TESTS_PASS when complete.",
        completion_promise="TESTS_PASS",
        max_iterations=30,
        timeout_seconds=1800,  # 30 minutes
        token_limit=500_000,
    ),
    "build-models": RalphPattern(
        name="build-models",
        description="Build dbt models incrementally until successful",
        prompt="Run 'dbt build' and fix any errors. Continue until all models build successfully. Output BUILD_COMPLETE when done.",
        completion_promise="BUILD_COMPLETE",
        max_iterations=25,
        timeout_seconds=2400,  # 40 minutes
        token_limit=500_000,
    ),
    "lint-fix": RalphPattern(
        name="lint-fix",
        description="Fix sqlfluff linting violations iteratively",
        prompt="Run 'sqlfluff lint' and fix violations. Continue until no violations remain. Output LINT_CLEAN when complete.",
        completion_promise="LINT_CLEAN",
        max_iterations=20,
        timeout_seconds=1200,  # 20 minutes
        token_limit=300_000,
    ),
    "test-and-lint": RalphPattern(
        name="test-and-lint",
        description="Fix both tests and lint issues until clean",
        prompt="Fix all dbt test failures and sqlfluff violations. Run tests and linting iteratively. Output ALL_CLEAN when both pass.",
        completion_promise="ALL_CLEAN",
        max_iterations=35,
        timeout_seconds=2400,  # 40 minutes
        token_limit=600_000,
    ),
    "fix-compilation": RalphPattern(
        name="fix-compilation",
        description="Fix dbt compilation errors",
        prompt="Run 'dbt compile' and fix any compilation errors. Continue until project compiles cleanly. Output COMPILE_SUCCESS when done.",
        completion_promise="COMPILE_SUCCESS",
        max_iterations=15,
        timeout_seconds=900,  # 15 minutes
        token_limit=250_000,
    ),
    "schema-tests": RalphPattern(
        name="schema-tests",
        description="Add and fix schema tests for all models",
        prompt="Ensure all models have schema tests (unique, not_null, relationships). Add missing tests and fix failures. Output SCHEMA_TESTS_COMPLETE when done.",
        completion_promise="SCHEMA_TESTS_COMPLETE",
        max_iterations=40,
        timeout_seconds=3600,  # 60 minutes
        token_limit=700_000,
    ),
    "docs-generate": RalphPattern(
        name="docs-generate",
        description="Generate and validate dbt documentation",
        prompt="Generate dbt documentation with 'dbt docs generate'. Ensure all models have descriptions and columns are documented. Output DOCS_COMPLETE when done.",
        completion_promise="DOCS_COMPLETE",
        max_iterations=20,
        timeout_seconds=1800,  # 30 minutes
        token_limit=400_000,
    ),
}


def start_dbt_ralph_pattern(
    agent: "DbtAgent",
    pattern_name: str,
    custom_prompt: str | None = None,
    **overrides,
) -> str:
    """Start a pre-configured dbt Ralph pattern.

    Args:
        agent: DbtAgent instance.
        pattern_name: Name of the pattern to use (from DBT_RALPH_PATTERNS).
        custom_prompt: Optional custom prompt to override pattern default.
        **overrides: Override pattern defaults (e.g., max_iterations=50).

    Returns:
        Status message indicating loop started.

    Raises:
        ValueError: If pattern_name is not found.

    Example:
        start_dbt_ralph_pattern(agent, "test-until-pass")
        start_dbt_ralph_pattern(agent, "lint-fix", max_iterations=30)
    """
    if pattern_name not in DBT_RALPH_PATTERNS:
        available = ", ".join(DBT_RALPH_PATTERNS.keys())
        raise ValueError(
            f"Unknown dbt Ralph pattern: {pattern_name}. "
            f"Available patterns: {available}"
        )

    pattern = DBT_RALPH_PATTERNS[pattern_name]

    # Apply overrides
    prompt = custom_prompt or pattern.prompt
    completion_promise = overrides.get("completion_promise", pattern.completion_promise)
    max_iterations = overrides.get("max_iterations", pattern.max_iterations)
    timeout_seconds = overrides.get("timeout_seconds", pattern.timeout_seconds)
    token_limit = overrides.get("token_limit", pattern.token_limit)

    # Start the Ralph loop
    agent.ralph_manager.start_loop(
        prompt=prompt,
        completion_promise=completion_promise,
        max_iterations=max_iterations,
        timeout_seconds=timeout_seconds,
        token_limit=token_limit,
    )

    # Format status message
    timeout_msg = f", {timeout_seconds}s timeout" if timeout_seconds else ""
    return (
        f"⟳ Started dbt Ralph pattern: {pattern_name}\n"
        f"Description: {pattern.description}\n"
        f"Max iterations: {max_iterations}{timeout_msg}, "
        f"{token_limit:,} token limit\n"
        f"Completing on: '{completion_promise}'"
    )


def list_dbt_ralph_patterns() -> str:
    """List all available dbt Ralph patterns.

    Returns:
        Formatted list of patterns with descriptions.

    Example:
        /ralph-patterns
    """
    lines = ["Available dbt Ralph patterns:", ""]

    for name, pattern in sorted(DBT_RALPH_PATTERNS.items()):
        lines.append(f"  {name}")
        lines.append(f"    {pattern.description}")
        lines.append(
            f"    {pattern.max_iterations} iterations, "
            f"completes on '{pattern.completion_promise}'"
        )
        lines.append("")

    lines.append("Usage:")
    lines.append("  /ralph-pattern <name>           # Use pattern")
    lines.append("  /ralph-pattern <name> --max-iterations 50  # Override settings")

    return "\n".join(lines)
