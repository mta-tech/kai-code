"""Fuzzy matching utilities and error builders for error suggestions.

This module provides utilities for fuzzy string matching to help generate
actionable error suggestions. It uses difflib for similarity matching and
provides specialized functions for file paths and commands.

It also provides error builder functions that construct ActionableError
instances for common error scenarios with appropriate suggestions.
"""
from __future__ import annotations

import difflib
import os
import stat
from pathlib import Path
from typing import Sequence

from kai_code.errors import ActionableError, ErrorType

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


# =============================================================================
# Error Builder Functions
# =============================================================================


def make_file_not_found_error(
    path: str | Path,
    search_dir: str | Path | None = None,
    n: int = DEFAULT_MAX_SUGGESTIONS,
    cutoff: float = DEFAULT_SIMILARITY_THRESHOLD,
) -> ActionableError:
    """Create an ActionableError for a file not found error.

    This function builds a comprehensive error message with similar file
    suggestions based on fuzzy matching.

    Args:
        path: The file path that was not found.
        search_dir: Directory to search for similar files. Defaults to
            the parent directory of the path, or current directory if path
            has no parent.
        n: Maximum number of similar files to suggest. Defaults to 3.
        cutoff: Similarity threshold (0.0 to 1.0). Defaults to 0.6.

    Returns:
        An ActionableError with suggestions for similar files and
        recovery commands.

    Example:
        >>> error = make_file_not_found_error("config.yaml", search_dir=".")
        >>> error.error_type
        <ErrorType.FILE_NOT_FOUND: 'file_not_found'>
        >>> "config.yaml" in error.message
        True
    """
    path_obj = Path(path)
    path_str = str(path)

    # Determine search directory
    if search_dir is not None:
        search_path = Path(search_dir)
    elif path_obj.parent and path_obj.parent != Path("."):
        search_path = path_obj.parent
    else:
        search_path = Path.cwd()

    # Find similar files
    similar = suggest_files(path_obj, search_dir=search_path, n=n, cutoff=cutoff)

    # Build suggestions
    suggestions = [
        "Check if the file path is spelled correctly",
        "Verify the file exists in the expected location",
    ]

    if not search_path.exists():
        suggestions.append(f"The directory '{search_path}' does not exist")
    elif search_path.is_dir():
        suggestions.append(f"Search in: {search_path.absolute()}")

    # Build recovery commands
    recovery_commands = [
        f"ls -la {search_path}" if search_path.exists() else f"ls -la .",
    ]

    # If looking for a specific file type, suggest find command
    if path_obj.suffix:
        recovery_commands.append(f"find . -name '*{path_obj.suffix}' -type f")

    return ActionableError(
        error_type=ErrorType.FILE_NOT_FOUND,
        message=f"File not found: '{path_str}'",
        suggestions=suggestions,
        recovery_commands=recovery_commands,
        related_items=similar,
        context={
            "path": path_str,
            "search_dir": str(search_path),
        },
    )


def make_file_permission_error(
    path: str | Path,
    operation: str = "access",
) -> ActionableError:
    """Create an ActionableError for a file permission error.

    This function builds an error message with chmod suggestions and
    information about the current file permissions.

    Args:
        path: The file path that caused the permission error.
        operation: The operation that failed (e.g., "read", "write", "execute").
            Defaults to "access".

    Returns:
        An ActionableError with chmod suggestions and recovery commands.

    Example:
        >>> error = make_file_permission_error("/etc/passwd", operation="write")
        >>> error.error_type
        <ErrorType.FILE_PERMISSION_DENIED: 'file_permission_denied'>
        >>> "chmod" in str(error.recovery_commands)
        True
    """
    path_obj = Path(path)
    path_str = str(path)

    # Determine what permissions are needed based on operation
    operation_lower = operation.lower()
    if operation_lower in ("read", "r"):
        needed_perm = "read"
        chmod_suggestion = "chmod +r"
        chmod_octal = "chmod 644"
    elif operation_lower in ("write", "w"):
        needed_perm = "write"
        chmod_suggestion = "chmod +w"
        chmod_octal = "chmod 644"
    elif operation_lower in ("execute", "exec", "x"):
        needed_perm = "execute"
        chmod_suggestion = "chmod +x"
        chmod_octal = "chmod 755"
    else:
        needed_perm = operation_lower
        chmod_suggestion = "chmod +rw"
        chmod_octal = "chmod 644"

    # Build suggestions
    suggestions = [
        f"You don't have {needed_perm} permission for this file",
        "Check if you own the file or have appropriate group permissions",
        "Consider using sudo if you need elevated privileges",
    ]

    # Try to get current permissions if file exists
    current_perms = None
    owner_info = None
    if path_obj.exists():
        try:
            file_stat = path_obj.stat()
            mode = file_stat.st_mode
            perms = stat.filemode(mode)
            current_perms = perms
            # Try to get owner info
            try:
                import pwd

                owner = pwd.getpwuid(file_stat.st_uid).pw_name
                owner_info = owner
            except (ImportError, KeyError):
                # pwd not available on Windows or user not found
                owner_info = str(file_stat.st_uid)
        except (OSError, PermissionError):
            pass

    # Build recovery commands
    recovery_commands = [
        f"{chmod_suggestion} {path_str}",
        f"{chmod_octal} {path_str}",
        f"ls -la {path_str}",
    ]

    # If operation is write and file doesn't exist, maybe parent dir issue
    if operation_lower in ("write", "w") and not path_obj.exists() and path_obj.parent.exists():
        recovery_commands.append(f"ls -la {path_obj.parent}")

    # Add sudo option for privileged operations
    recovery_commands.append(f"sudo {chmod_suggestion} {path_str}")

    # Build context
    context = {
        "path": path_str,
        "operation": operation,
    }
    if current_perms:
        context["current_permissions"] = current_perms
    if owner_info:
        context["owner"] = owner_info

    return ActionableError(
        error_type=ErrorType.FILE_PERMISSION_DENIED,
        message=f"Permission denied: cannot {operation} '{path_str}'",
        suggestions=suggestions,
        recovery_commands=recovery_commands,
        context=context,
    )


# Common file type mappings for conversion hints
FILE_TYPE_CONVERSIONS: dict[str, list[str]] = {
    ".yaml": [".yml", ".json", ".toml"],
    ".yml": [".yaml", ".json", ".toml"],
    ".json": [".yaml", ".yml", ".toml"],
    ".toml": [".yaml", ".yml", ".json"],
    ".py": [".pyw", ".pyi", ".pyc"],
    ".js": [".ts", ".mjs", ".cjs", ".jsx"],
    ".ts": [".js", ".tsx", ".mts", ".cts"],
    ".jsx": [".js", ".tsx"],
    ".tsx": [".ts", ".jsx"],
    ".md": [".txt", ".rst", ".html"],
    ".txt": [".md", ".rst"],
    ".csv": [".tsv", ".xlsx", ".json"],
    ".xlsx": [".csv", ".xls", ".json"],
    ".xls": [".xlsx", ".csv"],
    ".png": [".jpg", ".jpeg", ".gif", ".webp", ".svg"],
    ".jpg": [".png", ".jpeg", ".gif", ".webp"],
    ".jpeg": [".png", ".jpg", ".gif", ".webp"],
    ".gif": [".png", ".jpg", ".webp"],
    ".svg": [".png", ".pdf"],
    ".html": [".htm", ".md", ".pdf"],
    ".htm": [".html"],
    ".pdf": [".html", ".docx", ".md"],
    ".docx": [".doc", ".pdf", ".odt"],
    ".doc": [".docx", ".pdf"],
    ".mp3": [".wav", ".ogg", ".flac", ".m4a"],
    ".wav": [".mp3", ".ogg", ".flac"],
    ".mp4": [".webm", ".avi", ".mkv", ".mov"],
    ".webm": [".mp4", ".avi"],
}


def make_invalid_file_type_error(
    path: str | Path,
    expected_types: Sequence[str],
    conversion_hints: bool = True,
) -> ActionableError:
    """Create an ActionableError for an invalid file type error.

    This function builds an error message indicating the file type is not
    supported, with suggestions for conversion or alternative file types.

    Args:
        path: The file path with the invalid type.
        expected_types: List of expected file extensions (e.g., [".yaml", ".yml"]).
            Extensions should include the dot.
        conversion_hints: If True, include hints about file conversion tools.
            Defaults to True.

    Returns:
        An ActionableError with conversion hints and suggested alternatives.

    Example:
        >>> error = make_invalid_file_type_error("config.json", [".yaml", ".yml"])
        >>> error.error_type
        <ErrorType.INVALID_FILE_TYPE: 'invalid_file_type'>
        >>> ".yaml" in str(error.suggestions)
        True
    """
    path_obj = Path(path)
    path_str = str(path)
    actual_ext = path_obj.suffix.lower()
    filename = path_obj.name

    # Normalize expected types to include dots and be lowercase
    normalized_expected = []
    for ext in expected_types:
        ext_lower = ext.lower()
        if not ext_lower.startswith("."):
            ext_lower = f".{ext_lower}"
        normalized_expected.append(ext_lower)

    # Format expected types for display
    if len(normalized_expected) == 1:
        expected_display = f"'{normalized_expected[0]}'"
    elif len(normalized_expected) == 2:
        expected_display = f"'{normalized_expected[0]}' or '{normalized_expected[1]}'"
    else:
        expected_display = ", ".join(f"'{e}'" for e in normalized_expected[:-1])
        expected_display += f", or '{normalized_expected[-1]}'"

    # Build the main message
    if actual_ext:
        message = f"Invalid file type: '{filename}' has extension '{actual_ext}', expected {expected_display}"
    else:
        message = f"Invalid file type: '{filename}' has no extension, expected {expected_display}"

    # Build suggestions
    suggestions = [
        f"Rename the file to use one of the expected extensions: {expected_display}",
    ]

    # Add conversion hints if applicable
    if conversion_hints and actual_ext and actual_ext in FILE_TYPE_CONVERSIONS:
        convertible_to = FILE_TYPE_CONVERSIONS[actual_ext]
        matching_conversions = [ext for ext in convertible_to if ext in normalized_expected]
        if matching_conversions:
            suggestions.append(
                f"Convert the file from {actual_ext} to {matching_conversions[0]} format"
            )

    suggestions.append("Ensure you're using the correct file for this operation")

    # Build recovery commands
    recovery_commands = []

    # Suggest renaming with first expected extension
    if normalized_expected:
        new_name = path_obj.stem + normalized_expected[0]
        new_path = path_obj.parent / new_name if path_obj.parent != Path(".") else Path(new_name)
        recovery_commands.append(f"mv {path_str} {new_path}")

    # Add conversion tool suggestions based on file types
    if conversion_hints and actual_ext:
        conversion_tools = _get_conversion_tools(actual_ext, normalized_expected)
        recovery_commands.extend(conversion_tools)

    # Show what files exist with expected extensions
    if normalized_expected:
        ext_pattern = normalized_expected[0]
        recovery_commands.append(f"find . -name '*{ext_pattern}' -type f")

    # Build related items - suggest files with expected extensions in same directory
    related = []
    if path_obj.parent.exists() and path_obj.parent.is_dir():
        try:
            for expected_ext in normalized_expected[:2]:  # Check first 2 expected types
                for file in path_obj.parent.iterdir():
                    if file.is_file() and file.suffix.lower() == expected_ext:
                        related.append(str(file.relative_to(path_obj.parent)))
                        if len(related) >= 3:
                            break
                if len(related) >= 3:
                    break
        except (PermissionError, OSError):
            pass

    return ActionableError(
        error_type=ErrorType.INVALID_FILE_TYPE,
        message=message,
        suggestions=suggestions,
        recovery_commands=recovery_commands,
        related_items=related[:3],  # Limit to 3
        context={
            "path": path_str,
            "actual_type": actual_ext if actual_ext else "(none)",
            "expected_types": ", ".join(normalized_expected),
        },
    )


def _get_conversion_tools(
    source_ext: str,
    target_exts: Sequence[str],
) -> list[str]:
    """Get conversion tool suggestions for common file type conversions.

    Args:
        source_ext: The source file extension (e.g., ".json").
        target_exts: List of target extensions (e.g., [".yaml", ".yml"]).

    Returns:
        List of conversion tool command suggestions.
    """
    tools: list[str] = []
    source = source_ext.lower()
    targets = [t.lower() for t in target_exts]

    # JSON <-> YAML conversions
    if source == ".json" and (".yaml" in targets or ".yml" in targets):
        tools.append("# Use yq or python for conversion:")
        tools.append("yq -P file.json > file.yaml")
        tools.append("python -c \"import json, yaml; print(yaml.dump(json.load(open('file.json'))))\" > file.yaml")

    if source in (".yaml", ".yml") and ".json" in targets:
        tools.append("# Use yq or python for conversion:")
        tools.append("yq -o json file.yaml > file.json")
        tools.append("python -c \"import json, yaml; print(json.dumps(yaml.safe_load(open('file.yaml')), indent=2))\" > file.json")

    # Image conversions
    if source in (".png", ".jpg", ".jpeg", ".gif", ".webp"):
        for target in targets:
            if target in (".png", ".jpg", ".jpeg", ".gif", ".webp"):
                tools.append(f"# Use ImageMagick for conversion:")
                tools.append(f"convert input{source} output{target}")
                break

    # Document conversions
    if source in (".md", ".html", ".docx", ".pdf"):
        for target in targets:
            if target in (".md", ".html", ".docx", ".pdf"):
                tools.append("# Use pandoc for conversion:")
                tools.append(f"pandoc input{source} -o output{target}")
                break

    # CSV <-> JSON
    if source == ".csv" and ".json" in targets:
        tools.append("# Use csvjson or python for conversion:")
        tools.append("csvjson file.csv > file.json")

    if source == ".json" and ".csv" in targets:
        tools.append("# Use in2csv or python for conversion:")
        tools.append("in2csv file.json > file.csv")

    return tools
