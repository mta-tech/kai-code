"""Fuzzy matching utilities for error suggestions.

This module provides utilities for fuzzy string matching to help generate
actionable error suggestions. It uses difflib for similarity matching and
provides specialized functions for file paths and commands.
"""
from __future__ import annotations

import difflib
from pathlib import Path
from typing import Sequence

# Default threshold for fuzzy matching (0.0 to 1.0)
# Higher values require closer matches
DEFAULT_SIMILARITY_THRESHOLD = 0.6

# Maximum number of suggestions to return by default
DEFAULT_MAX_SUGGESTIONS = 3


def similar_strings(
    target: str,
    candidates: Sequence[str],
    n: int = DEFAULT_MAX_SUGGESTIONS,
    cutoff: float = DEFAULT_SIMILARITY_THRESHOLD,
) -> list[str]:
    """Find strings similar to the target from a list of candidates.

    Uses difflib.get_close_matches for fuzzy string matching based on
    sequence similarity (Gestalt pattern matching).

    Args:
        target: The string to find matches for.
        candidates: A sequence of strings to search through.
        n: Maximum number of close matches to return. Defaults to 3.
        cutoff: Similarity threshold (0.0 to 1.0). Strings with a similarity
            ratio below this are ignored. Defaults to 0.6.

    Returns:
        A list of similar strings from candidates, sorted by similarity
        (most similar first). Returns an empty list if no matches found.

    Example:
        >>> similar_strings("config.yaml", ["config.yml", "settings.yaml", "data.json"])
        ['config.yml', 'settings.yaml']
    """
    if not target or not candidates:
        return []

    # Filter out empty strings from candidates
    valid_candidates = [c for c in candidates if c]
    if not valid_candidates:
        return []

    return difflib.get_close_matches(target, valid_candidates, n=n, cutoff=cutoff)


def suggest_files(
    target_path: str | Path,
    search_dir: str | Path | None = None,
    n: int = DEFAULT_MAX_SUGGESTIONS,
    cutoff: float = DEFAULT_SIMILARITY_THRESHOLD,
    extensions: Sequence[str] | None = None,
    recursive: bool = True,
) -> list[str]:
    """Find files with similar names to the target path.

    Searches a directory for files with similar names to help users find
    files they may have mistyped.

    Args:
        target_path: The file path to find matches for. Can be just a filename
            or a full path (only the filename is used for matching).
        search_dir: Directory to search in. Defaults to current working directory.
        n: Maximum number of suggestions to return. Defaults to 3.
        cutoff: Similarity threshold (0.0 to 1.0). Defaults to 0.6.
        extensions: If provided, only consider files with these extensions
            (e.g., [".py", ".yaml"]). Extensions should include the dot.
        recursive: If True, search subdirectories recursively. Defaults to True.

    Returns:
        A list of relative file paths similar to the target, sorted by
        similarity. Returns an empty list if no matches found or directory
        doesn't exist.

    Example:
        >>> suggest_files("config.yaml", search_dir=".")
        ['config.yml', 'configs/config.yaml']
    """
    # Convert to Path objects
    target = Path(target_path)
    search_path = Path(search_dir) if search_dir else Path.cwd()

    if not search_path.exists() or not search_path.is_dir():
        return []

    # Extract just the filename for matching
    target_name = target.name

    # Collect all files in the search directory
    try:
        if recursive:
            all_files = list(search_path.rglob("*"))
        else:
            all_files = list(search_path.glob("*"))
    except (PermissionError, OSError):
        return []

    # Filter to only files (not directories)
    file_paths = [f for f in all_files if f.is_file()]

    # Filter by extensions if provided
    if extensions:
        normalized_extensions = [ext if ext.startswith(".") else f".{ext}" for ext in extensions]
        file_paths = [f for f in file_paths if f.suffix.lower() in normalized_extensions]

    # Get relative paths for display
    relative_paths: dict[str, Path] = {}
    for file_path in file_paths:
        try:
            rel_path = file_path.relative_to(search_path)
            relative_paths[file_path.name] = rel_path
        except ValueError:
            # File is not relative to search_path, skip
            continue

    if not relative_paths:
        return []

    # Find similar filenames
    similar_names = similar_strings(target_name, list(relative_paths.keys()), n=n * 2, cutoff=cutoff)

    # Return the relative paths for matching filenames
    result = []
    seen_paths = set()
    for name in similar_names:
        rel_path = relative_paths.get(name)
        if rel_path:
            path_str = str(rel_path)
            if path_str not in seen_paths:
                result.append(path_str)
                seen_paths.add(path_str)
                if len(result) >= n:
                    break

    return result


def suggest_commands(
    target_command: str,
    available_commands: Sequence[str],
    n: int = DEFAULT_MAX_SUGGESTIONS,
    cutoff: float = DEFAULT_SIMILARITY_THRESHOLD,
) -> list[str]:
    """Find commands similar to the target from available commands.

    Helps users who mistype command names by suggesting similar valid commands.

    Args:
        target_command: The command the user typed (may be misspelled).
        available_commands: List of valid command names to search through.
        n: Maximum number of suggestions to return. Defaults to 3.
        cutoff: Similarity threshold (0.0 to 1.0). Defaults to 0.6.

    Returns:
        A list of similar command names, sorted by similarity.
        Returns an empty list if no matches found.

    Example:
        >>> suggest_commands("/healp", ["/help", "/clear", "/quit", "/tokens"])
        ['/help']
    """
    if not target_command or not available_commands:
        return []

    # Normalize the target command (strip whitespace, lowercase for matching)
    normalized_target = target_command.strip().lower()

    # For commands with prefixes (like /help or --version), try matching
    # both with and without the prefix
    prefixes = ["/", "--", "-"]
    target_without_prefix = normalized_target
    for prefix in prefixes:
        if normalized_target.startswith(prefix):
            target_without_prefix = normalized_target[len(prefix) :]
            break

    # Build a mapping of normalized commands to original commands
    command_map: dict[str, str] = {}
    for cmd in available_commands:
        if cmd:
            normalized = cmd.strip().lower()
            command_map[normalized] = cmd

    # Try matching with the full command first
    matches = similar_strings(normalized_target, list(command_map.keys()), n=n, cutoff=cutoff)

    # If no matches and we have a prefix, try matching without prefix
    if not matches and target_without_prefix != normalized_target:
        # Create versions without prefixes for matching
        stripped_commands: dict[str, str] = {}
        for norm_cmd, orig_cmd in command_map.items():
            stripped = norm_cmd
            for prefix in prefixes:
                if norm_cmd.startswith(prefix):
                    stripped = norm_cmd[len(prefix) :]
                    break
            stripped_commands[stripped] = orig_cmd

        stripped_matches = similar_strings(
            target_without_prefix, list(stripped_commands.keys()), n=n, cutoff=cutoff
        )
        # Map back to original commands
        matches = [
            command_map.get(stripped_commands.get(m, "").lower(), stripped_commands.get(m, ""))
            for m in stripped_matches
        ]
        matches = [m for m in matches if m]  # Filter out empty strings

    # Return original command names (preserving original casing)
    result = [command_map.get(m, m) for m in matches]
    return result[:n]


def suggest_flags(
    target_flag: str,
    valid_flags: Sequence[str],
    n: int = DEFAULT_MAX_SUGGESTIONS,
    cutoff: float = DEFAULT_SIMILARITY_THRESHOLD,
) -> list[str]:
    """Find flags similar to the target from valid flags.

    Helps users who mistype command flags by suggesting similar valid flags.

    Args:
        target_flag: The flag the user typed (may be misspelled).
        valid_flags: List of valid flag names (e.g., ["--help", "--verbose"]).
        n: Maximum number of suggestions to return. Defaults to 3.
        cutoff: Similarity threshold (0.0 to 1.0). Defaults to 0.6.

    Returns:
        A list of similar flag names, sorted by similarity.
        Returns an empty list if no matches found.

    Example:
        >>> suggest_flags("--versboe", ["--help", "--verbose", "--quiet"])
        ['--verbose']
    """
    # Use the same logic as suggest_commands since flags have similar structure
    return suggest_commands(target_flag, valid_flags, n=n, cutoff=cutoff)


def suggest_values(
    target_value: str,
    valid_values: Sequence[str],
    n: int = DEFAULT_MAX_SUGGESTIONS,
    cutoff: float = DEFAULT_SIMILARITY_THRESHOLD,
) -> list[str]:
    """Find values similar to the target from valid values.

    Generic helper for suggesting similar values (models, providers, etc.).

    Args:
        target_value: The value the user provided (may be misspelled).
        valid_values: List of valid values to search through.
        n: Maximum number of suggestions to return. Defaults to 3.
        cutoff: Similarity threshold (0.0 to 1.0). Defaults to 0.6.

    Returns:
        A list of similar values, sorted by similarity.
        Returns an empty list if no matches found.

    Example:
        >>> suggest_values("gpt-4o-mni", ["gpt-4o-mini", "gpt-4o", "gpt-4"])
        ['gpt-4o-mini', 'gpt-4o']
    """
    return similar_strings(target_value, valid_values, n=n, cutoff=cutoff)
