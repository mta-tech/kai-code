"""Prompt loader with lazy loading and selective inheritance support.

This module provides a system for loading markdown-based system prompts
with support for inheritance between prompt files.

Usage:
    from kai_code.prompts import load_prompt

    # Load the base kai-code prompt
    prompt = load_prompt("kai-code")

    # Load kai-dbt (inherits from kai-code)
    dbt_prompt = load_prompt("kai-dbt")

Inheritance:
    Prompts can inherit from other prompts using the INHERIT directive:

        # INHERIT: kai-code

    This will prepend the inherited prompt's content before the current prompt.
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

# Directory containing prompt markdown files
PROMPTS_DIR = Path(__file__).parent

# Regex patterns for parsing directives
INHERIT_PATTERN = re.compile(r"^#\s*INHERIT:\s*(\S+)\s*$", re.MULTILINE)
OVERRIDE_PATTERN = re.compile(r"^#\s*OVERRIDE:\s*(\S+)\s*$", re.MULTILINE)

# Cache for loaded prompts
_prompt_cache: dict[str, str] = {}


def get_prompt_path(name: str) -> Path:
    """Get the path to a prompt file.

    Args:
        name: Prompt name (e.g., "kai-code", "kai-dbt")

    Returns:
        Path to the prompt markdown file

    Raises:
        FileNotFoundError: If prompt file doesn't exist
    """
    prompt_path = PROMPTS_DIR / f"{name}.md"
    if not prompt_path.exists():
        available = list_prompts()
        raise FileNotFoundError(
            f"Prompt '{name}' not found. Available prompts: {available}"
        )
    return prompt_path


def list_prompts() -> list[str]:
    """List all available prompt names.

    Returns:
        List of prompt names (without .md extension)
    """
    return [
        p.stem
        for p in PROMPTS_DIR.glob("*.md")
        if p.is_file() and not p.name.startswith("_")
    ]


def _parse_inherit_directive(content: str) -> str | None:
    """Extract the inherit directive from prompt content.

    Args:
        content: Raw prompt file content

    Returns:
        Name of prompt to inherit from, or None if no directive
    """
    match = INHERIT_PATTERN.search(content)
    if match:
        return match.group(1).strip()
    return None


def _remove_directives(content: str) -> str:
    """Remove INHERIT and OVERRIDE directives from content.

    Args:
        content: Raw prompt content with directives

    Returns:
        Content with directives removed
    """
    # Remove INHERIT lines
    content = INHERIT_PATTERN.sub("", content)
    # Remove OVERRIDE lines
    content = OVERRIDE_PATTERN.sub("", content)
    return content.strip()


def _load_raw_prompt(name: str) -> str:
    """Load raw prompt content from file without processing.

    Args:
        name: Prompt name

    Returns:
        Raw file content
    """
    prompt_path = get_prompt_path(name)
    return prompt_path.read_text(encoding="utf-8")


def load_prompt(name: str, *, use_cache: bool = True) -> str:
    """Load a prompt by name with inheritance support.

    This function loads a prompt markdown file and applies inheritance
    if the INHERIT directive is present. Inherited prompts are prepended
    to the current prompt content.

    Args:
        name: Prompt name (e.g., "kai-code", "kai-dbt")
        use_cache: Whether to use cached prompts (default: True)

    Returns:
        Full prompt string with inheritance applied

    Raises:
        FileNotFoundError: If prompt file doesn't exist
        RecursionError: If circular inheritance is detected

    Example:
        >>> prompt = load_prompt("kai-code")
        >>> len(prompt) > 0
        True

        >>> dbt_prompt = load_prompt("kai-dbt")
        >>> "dbt" in dbt_prompt.lower()
        True
    """
    # Check cache first
    if use_cache and name in _prompt_cache:
        return _prompt_cache[name]

    # Track inheritance chain to detect cycles
    return _load_prompt_with_chain(name, chain=set(), use_cache=use_cache)


def _load_prompt_with_chain(
    name: str, chain: set[str], *, use_cache: bool = True
) -> str:
    """Load prompt with inheritance chain tracking.

    Args:
        name: Prompt name
        chain: Set of prompts already in inheritance chain
        use_cache: Whether to use cached prompts

    Returns:
        Full prompt string

    Raises:
        RecursionError: If circular inheritance detected
    """
    # Detect circular inheritance
    if name in chain:
        raise RecursionError(
            f"Circular inheritance detected: {name} -> {' -> '.join(chain)} -> {name}"
        )

    # Check cache
    if use_cache and name in _prompt_cache:
        return _prompt_cache[name]

    # Load raw content
    raw_content = _load_raw_prompt(name)

    # Check for inheritance
    parent_name = _parse_inherit_directive(raw_content)

    # Clean content (remove directives)
    clean_content = _remove_directives(raw_content)

    # Build final prompt
    if parent_name:
        # Add current name to chain and load parent
        new_chain = chain | {name}
        parent_content = _load_prompt_with_chain(
            parent_name, new_chain, use_cache=use_cache
        )
        # Combine: parent first, then child
        final_content = f"{parent_content}\n\n---\n\n{clean_content}"
    else:
        final_content = clean_content

    # Cache the result
    if use_cache:
        _prompt_cache[name] = final_content

    return final_content


def clear_cache() -> None:
    """Clear the prompt cache.

    Useful for development/testing when prompt files are modified.
    """
    _prompt_cache.clear()


@lru_cache(maxsize=16)
def get_prompt_metadata(name: str) -> dict[str, str | None]:
    """Get metadata about a prompt.

    Args:
        name: Prompt name

    Returns:
        Dict with metadata:
            - path: File path
            - inherits: Parent prompt name or None
            - lines: Line count
    """
    prompt_path = get_prompt_path(name)
    raw_content = prompt_path.read_text(encoding="utf-8")

    return {
        "path": str(prompt_path),
        "inherits": _parse_inherit_directive(raw_content),
        "lines": str(len(raw_content.splitlines())),
    }


# Public API
__all__ = [
    "load_prompt",
    "get_prompt_path",
    "list_prompts",
    "get_prompt_metadata",
    "clear_cache",
    "PROMPTS_DIR",
]
