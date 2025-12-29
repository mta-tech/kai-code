"""System prompt resolution with backwards compatibility.

This module provides backwards-compatible system prompt resolution,
mapping legacy prompt IDs to the new markdown-based prompt system.
"""
from __future__ import annotations

from kai_code.prompts import load_prompt

# Legacy prompt IDs mapped to new prompt names
_LEGACY_PROMPT_MAP: dict[str, str] = {
    "kai-default": "kai-code",
    "kai-code": "kai-code",
    "kai-dbt": "kai-dbt",
}

# Legacy simple prompts for IDs that don't have markdown files
_LEGACY_SIMPLE_PROMPTS: dict[str, str] = {
    "plan": "You are Kai Code. Produce a concrete implementation plan before editing files. Prefer read-only exploration and ask before executing risky commands.",
    "fix": "You are Kai Code. Focus on debugging and fixing failing tests. Make minimal changes and rerun validators.",
}


def resolve_system_prompt(*, system_id: str | None, extra: str | None) -> str | None:
    """Resolve a system prompt by ID with optional extra content.

    This function maintains backwards compatibility with the old prompt system
    while using the new markdown-based prompts internally.

    Args:
        system_id: Prompt identifier (e.g., "kai-default", "kai-code", "kai-dbt")
        extra: Additional prompt content to append

    Returns:
        Resolved system prompt string, or None if no prompt specified
    """
    base: str | None = None

    if system_id:
        # Check if it maps to a new markdown prompt
        if system_id in _LEGACY_PROMPT_MAP:
            prompt_name = _LEGACY_PROMPT_MAP[system_id]
            try:
                base = load_prompt(prompt_name)
            except FileNotFoundError:
                # Fall back to simple prompt if markdown not found
                base = _LEGACY_SIMPLE_PROMPTS.get(system_id)
        else:
            # Check legacy simple prompts
            base = _LEGACY_SIMPLE_PROMPTS.get(system_id)

    # Combine base and extra
    if base and extra:
        return base.rstrip() + "\n\n" + extra.strip()
    return base or (extra.strip() if extra else None)


def get_prompt(name: str) -> str:
    """Get a prompt by name.

    This is the preferred way to get prompts. Use system IDs like
    "kai-code" or "kai-dbt" to get the full markdown-based prompts.

    Args:
        name: Prompt name

    Returns:
        Prompt content

    Raises:
        FileNotFoundError: If prompt not found
    """
    return load_prompt(name)


# Backwards compatibility: expose old dict interface (read-only)
SYSTEM_PROMPTS: dict[str, str] = {
    "kai-default": "You are Kai Code, a software engineering agent. Work in the current repository. Prefer small, safe, incremental changes and run validators.",
    "plan": _LEGACY_SIMPLE_PROMPTS["plan"],
    "fix": _LEGACY_SIMPLE_PROMPTS["fix"],
}
