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


# =============================================================================
# Command Error Builder Functions
# =============================================================================


def make_unknown_command_error(
    cmd: str,
    available_commands: Sequence[str],
    n: int = DEFAULT_MAX_SUGGESTIONS,
    cutoff: float = DEFAULT_SIMILARITY_THRESHOLD,
) -> ActionableError:
    """Create an ActionableError for an unknown command error.

    This function builds an error message with similar command suggestions
    based on fuzzy matching against available commands.

    Args:
        cmd: The command that was not recognized.
        available_commands: List of valid commands to search through.
        n: Maximum number of similar commands to suggest. Defaults to 3.
        cutoff: Similarity threshold (0.0 to 1.0). Defaults to 0.6.

    Returns:
        An ActionableError with suggestions for similar commands and
        a list of available commands.

    Example:
        >>> error = make_unknown_command_error("/healp", ["/help", "/clear", "/quit"])
        >>> error.error_type
        <ErrorType.COMMAND_NOT_FOUND: 'command_not_found'>
        >>> "/help" in error.related_items
        True
    """
    cmd_str = cmd.strip()

    # Find similar commands
    similar = suggest_commands(cmd_str, available_commands, n=n, cutoff=cutoff)

    # Build suggestions
    suggestions = [
        "Check if the command is spelled correctly",
        "Use '/help' or '--help' to see available commands",
    ]

    # Mention if it looks like a typo of a common command
    if similar:
        if len(similar) == 1:
            suggestions.insert(0, f"Did you mean '{similar[0]}'?")
        else:
            suggestions.insert(0, f"Similar commands: {', '.join(similar)}")

    # Build recovery commands
    recovery_commands = [
        "/help",
    ]

    # If available commands is small enough, show them
    if len(available_commands) <= 10:
        # Show available commands as a suggestion
        suggestions.append(
            f"Available commands: {', '.join(sorted(available_commands))}"
        )

    return ActionableError(
        error_type=ErrorType.COMMAND_NOT_FOUND,
        message=f"Unknown command: '{cmd_str}'",
        suggestions=suggestions,
        recovery_commands=recovery_commands,
        related_items=similar,
        context={
            "command": cmd_str,
            "available_count": str(len(available_commands)),
        },
    )


def make_invalid_flag_error(
    flag: str,
    valid_flags: Sequence[str],
    command: str | None = None,
    n: int = DEFAULT_MAX_SUGGESTIONS,
    cutoff: float = DEFAULT_SIMILARITY_THRESHOLD,
) -> ActionableError:
    """Create an ActionableError for an invalid flag error.

    This function builds an error message with similar flag suggestions
    based on fuzzy matching against valid flags.

    Args:
        flag: The flag that was not recognized.
        valid_flags: List of valid flags for the command.
        command: The command the flag was used with (optional, for context).
        n: Maximum number of similar flags to suggest. Defaults to 3.
        cutoff: Similarity threshold (0.0 to 1.0). Defaults to 0.6.

    Returns:
        An ActionableError with suggestions for similar flags and
        usage help.

    Example:
        >>> error = make_invalid_flag_error("--versboe", ["--help", "--verbose", "--quiet"])
        >>> error.error_type
        <ErrorType.INVALID_FLAG: 'invalid_flag'>
        >>> "--verbose" in error.related_items
        True
    """
    flag_str = flag.strip()

    # Find similar flags
    similar = suggest_flags(flag_str, valid_flags, n=n, cutoff=cutoff)

    # Build the main message
    if command:
        message = f"Invalid flag '{flag_str}' for command '{command}'"
    else:
        message = f"Invalid flag: '{flag_str}'"

    # Build suggestions
    suggestions = [
        "Check if the flag is spelled correctly",
        "Flags are case-sensitive",
    ]

    # Mention if it looks like a typo of a known flag
    if similar:
        if len(similar) == 1:
            suggestions.insert(0, f"Did you mean '{similar[0]}'?")
        else:
            suggestions.insert(0, f"Similar flags: {', '.join(similar)}")

    # Build recovery commands
    recovery_commands = []
    if command:
        recovery_commands.append(f"{command} --help")
    else:
        recovery_commands.append("--help")

    # Show valid flags if not too many
    if len(valid_flags) <= 10:
        # Format flags nicely for display
        formatted_flags = ", ".join(sorted(valid_flags))
        suggestions.append(f"Valid flags: {formatted_flags}")
    elif len(valid_flags) > 0:
        suggestions.append(f"Use --help to see all {len(valid_flags)} available flags")

    # Build context
    context = {
        "flag": flag_str,
        "valid_flags_count": str(len(valid_flags)),
    }
    if command:
        context["command"] = command

    return ActionableError(
        error_type=ErrorType.INVALID_FLAG,
        message=message,
        suggestions=suggestions,
        recovery_commands=recovery_commands,
        related_items=similar,
        context=context,
    )


def make_missing_argument_error(
    command: str,
    missing_arg: str,
    expected_type: str | None = None,
    usage_example: str | None = None,
) -> ActionableError:
    """Create an ActionableError for a missing required argument error.

    This function builds an error message indicating a required argument
    is missing, with usage examples and suggestions.

    Args:
        command: The command that requires the argument.
        missing_arg: The name of the missing argument.
        expected_type: Optional description of what type/format is expected
            (e.g., "file path", "integer", "model name").
        usage_example: Optional example of correct usage.

    Returns:
        An ActionableError with usage instructions and suggestions.

    Example:
        >>> error = make_missing_argument_error("/model", "model_name", expected_type="model identifier")
        >>> error.error_type
        <ErrorType.MISSING_ARGUMENT: 'missing_argument'>
        >>> "model_name" in error.message
        True
    """
    command_str = command.strip()
    arg_str = missing_arg.strip()

    # Build the main message
    message = f"Missing required argument '{arg_str}' for command '{command_str}'"

    # Build suggestions
    suggestions = [
        f"Provide the required '{arg_str}' argument",
    ]

    if expected_type:
        suggestions.append(f"Expected: {expected_type}")

    suggestions.append("Check the command syntax and try again")

    # Build recovery commands with help
    recovery_commands = [
        f"{command_str} --help",
    ]

    # Add usage example if provided
    if usage_example:
        recovery_commands.insert(0, f"# Example: {usage_example}")

    # Build context
    context = {
        "command": command_str,
        "missing_argument": arg_str,
    }
    if expected_type:
        context["expected_type"] = expected_type

    return ActionableError(
        error_type=ErrorType.MISSING_ARGUMENT,
        message=message,
        suggestions=suggestions,
        recovery_commands=recovery_commands,
        context=context,
    )


# =============================================================================
# Configuration Error Builder Functions
# =============================================================================

# Provider-specific API key setup instructions
PROVIDER_API_KEY_INSTRUCTIONS: dict[str, dict[str, str]] = {
    "anthropic": {
        "env_var": "ANTHROPIC_API_KEY",
        "url": "https://console.anthropic.com/settings/keys",
        "description": "Anthropic (Claude)",
    },
    "openai": {
        "env_var": "OPENAI_API_KEY",
        "url": "https://platform.openai.com/api-keys",
        "description": "OpenAI (GPT)",
    },
    "google": {
        "env_var": "GOOGLE_API_KEY",
        "url": "https://aistudio.google.com/app/apikey",
        "description": "Google (Gemini)",
    },
    "gemini": {
        "env_var": "GOOGLE_API_KEY",
        "url": "https://aistudio.google.com/app/apikey",
        "description": "Google (Gemini)",
    },
    "mistral": {
        "env_var": "MISTRAL_API_KEY",
        "url": "https://console.mistral.ai/api-keys/",
        "description": "Mistral AI",
    },
    "groq": {
        "env_var": "GROQ_API_KEY",
        "url": "https://console.groq.com/keys",
        "description": "Groq",
    },
    "ollama": {
        "env_var": "",  # Ollama doesn't require API key by default
        "url": "https://ollama.ai/",
        "description": "Ollama (local)",
    },
}


def make_api_key_missing_error(
    provider: str,
) -> ActionableError:
    """Create an ActionableError for a missing API key error.

    This function builds an error message with provider-specific instructions
    for obtaining and setting up an API key.

    Args:
        provider: The name of the AI provider (e.g., "anthropic", "openai", "google").

    Returns:
        An ActionableError with setup instructions and recovery commands.

    Example:
        >>> error = make_api_key_missing_error("anthropic")
        >>> error.error_type
        <ErrorType.API_KEY_MISSING: 'api_key_missing'>
        >>> "ANTHROPIC_API_KEY" in str(error.suggestions)
        True
    """
    provider_lower = provider.lower().strip()

    # Get provider-specific info
    provider_info = PROVIDER_API_KEY_INSTRUCTIONS.get(provider_lower)

    if provider_info:
        env_var = provider_info["env_var"]
        url = provider_info["url"]
        description = provider_info["description"]
    else:
        # Generic fallback for unknown providers
        env_var = f"{provider.upper().replace(' ', '_').replace('-', '_')}_API_KEY"
        url = ""
        description = provider

    # Special case for Ollama which doesn't need an API key
    if provider_lower == "ollama":
        message = f"Ollama is not running or not accessible"
        suggestions = [
            "Make sure Ollama is installed and running",
            "Check if Ollama is running with 'ollama list'",
            "Start Ollama with 'ollama serve' if not running",
        ]
        recovery_commands = [
            "ollama list",
            "ollama serve",
        ]
        context = {
            "provider": description,
        }
        return ActionableError(
            error_type=ErrorType.API_KEY_MISSING,
            message=message,
            suggestions=suggestions,
            recovery_commands=recovery_commands,
            context=context,
        )

    # Build the main message
    message = f"API key not configured for {description}"

    # Build suggestions
    suggestions = [
        f"Set the {env_var} environment variable with your API key",
    ]

    if url:
        suggestions.append(f"Get your API key from: {url}")

    suggestions.extend([
        f"Add 'export {env_var}=your-key-here' to your shell profile",
        "Or create a .env file in your project directory",
    ])

    # Build recovery commands
    recovery_commands = [
        f"# Set the API key in your current session:",
        f"export {env_var}=your-api-key-here",
    ]

    if url:
        recovery_commands.extend([
            f"# Get your API key from:",
            f"# {url}",
        ])

    recovery_commands.extend([
        f"# Or add to ~/.bashrc or ~/.zshrc:",
        f"echo 'export {env_var}=your-api-key-here' >> ~/.bashrc",
    ])

    # Build context
    context = {
        "provider": description,
        "env_var": env_var,
    }
    if url:
        context["api_key_url"] = url

    return ActionableError(
        error_type=ErrorType.API_KEY_MISSING,
        message=message,
        suggestions=suggestions,
        recovery_commands=recovery_commands,
        context=context,
    )


def make_model_not_available_error(
    model: str,
    available_models: Sequence[str],
    n: int = DEFAULT_MAX_SUGGESTIONS,
    cutoff: float = DEFAULT_SIMILARITY_THRESHOLD,
) -> ActionableError:
    """Create an ActionableError for a model not available error.

    This function builds an error message with similar model suggestions
    based on fuzzy matching against available models.

    Args:
        model: The model name that was requested but not available.
        available_models: List of available model names to search through.
        n: Maximum number of similar models to suggest. Defaults to 3.
        cutoff: Similarity threshold (0.0 to 1.0). Defaults to 0.6.

    Returns:
        An ActionableError with suggestions for similar models and
        a list of available models.

    Example:
        >>> error = make_model_not_available_error("gpt-4o-mni", ["gpt-4o-mini", "gpt-4o", "gpt-4"])
        >>> error.error_type
        <ErrorType.MODEL_NOT_AVAILABLE: 'model_not_available'>
        >>> "gpt-4o-mini" in error.related_items
        True
    """
    model_str = model.strip()

    # Find similar models
    similar = suggest_values(model_str, available_models, n=n, cutoff=cutoff)

    # Build the main message
    message = f"Model '{model_str}' is not available"

    # Build suggestions
    suggestions = [
        "Check if the model name is spelled correctly",
    ]

    # Mention if it looks like a typo of an available model
    if similar:
        if len(similar) == 1:
            suggestions.insert(0, f"Did you mean '{similar[0]}'?")
        else:
            suggestions.insert(0, f"Similar models: {', '.join(similar)}")

    # If few available models, list them all
    if len(available_models) <= 10 and available_models:
        formatted_models = ", ".join(sorted(available_models))
        suggestions.append(f"Available models: {formatted_models}")
    elif available_models:
        suggestions.append(f"Use '/models' to see all {len(available_models)} available models")
    else:
        suggestions.append("No models are currently available - check your API key configuration")

    suggestions.append("Some models may require specific API keys or permissions")

    # Build recovery commands
    recovery_commands = [
        "/models",
    ]

    # If we have a similar model, suggest using it
    if similar:
        recovery_commands.insert(0, f"/model {similar[0]}")

    # Build context
    context = {
        "requested_model": model_str,
        "available_count": str(len(available_models)),
    }

    return ActionableError(
        error_type=ErrorType.MODEL_NOT_AVAILABLE,
        message=message,
        suggestions=suggestions,
        recovery_commands=recovery_commands,
        related_items=similar,
        context=context,
    )


def make_skill_not_found_error(
    skill_id: str,
    available_skills: Sequence[str],
    n: int = DEFAULT_MAX_SUGGESTIONS,
    cutoff: float = DEFAULT_SIMILARITY_THRESHOLD,
) -> ActionableError:
    """Create an ActionableError for a skill not found error.

    This function builds an error message with similar skill suggestions
    based on fuzzy matching against available skills.

    Args:
        skill_id: The skill identifier that was not found.
        available_skills: List of available skill identifiers to search through.
        n: Maximum number of similar skills to suggest. Defaults to 3.
        cutoff: Similarity threshold (0.0 to 1.0). Defaults to 0.6.

    Returns:
        An ActionableError with suggestions for similar skills and
        a list of available skills.

    Example:
        >>> error = make_skill_not_found_error("code-reveiw", ["code-review", "code-explain", "code-refactor"])
        >>> error.error_type
        <ErrorType.SKILL_NOT_FOUND: 'skill_not_found'>
        >>> "code-review" in error.related_items
        True
    """
    skill_str = skill_id.strip()

    # Find similar skills
    similar = suggest_values(skill_str, available_skills, n=n, cutoff=cutoff)

    # Build the main message
    message = f"Skill '{skill_str}' not found"

    # Build suggestions
    suggestions = [
        "Check if the skill name is spelled correctly",
    ]

    # Mention if it looks like a typo of an available skill
    if similar:
        if len(similar) == 1:
            suggestions.insert(0, f"Did you mean '{similar[0]}'?")
        else:
            suggestions.insert(0, f"Similar skills: {', '.join(similar)}")

    # If few available skills, list them all
    if len(available_skills) <= 10 and available_skills:
        formatted_skills = ", ".join(sorted(available_skills))
        suggestions.append(f"Available skills: {formatted_skills}")
    elif available_skills:
        suggestions.append(f"Use '/skills' to see all {len(available_skills)} available skills")
    else:
        suggestions.append("No skills are currently loaded")

    suggestions.append("Skills can be loaded from local directories or installed packages")

    # Build recovery commands
    recovery_commands = [
        "/skills",
    ]

    # If we have a similar skill, suggest loading it
    if similar:
        recovery_commands.insert(0, f"/skill load {similar[0]}")

    recovery_commands.append("/skill reload")

    # Build context
    context = {
        "requested_skill": skill_str,
        "available_count": str(len(available_skills)),
    }

    return ActionableError(
        error_type=ErrorType.SKILL_NOT_FOUND,
        message=message,
        suggestions=suggestions,
        recovery_commands=recovery_commands,
        related_items=similar,
        context=context,
    )


# =============================================================================
# DBT Error Builder Functions
# =============================================================================

# Common database adapter instructions for dbt
DBT_DATABASE_ADAPTERS: dict[str, dict[str, str]] = {
    "duckdb": {
        "check_command": "duckdb --version",
        "install_command": "pip install dbt-duckdb",
        "connection_format": "path/to/database.duckdb",
        "description": "DuckDB (file-based analytics database)",
    },
    "postgres": {
        "check_command": "psql --version",
        "install_command": "pip install dbt-postgres",
        "connection_format": "postgresql://user:password@host:port/database",
        "description": "PostgreSQL",
    },
    "postgresql": {
        "check_command": "psql --version",
        "install_command": "pip install dbt-postgres",
        "connection_format": "postgresql://user:password@host:port/database",
        "description": "PostgreSQL",
    },
    "snowflake": {
        "check_command": "snowsql --version",
        "install_command": "pip install dbt-snowflake",
        "connection_format": "account/database/schema",
        "description": "Snowflake",
    },
    "bigquery": {
        "check_command": "bq --version",
        "install_command": "pip install dbt-bigquery",
        "connection_format": "project_id/dataset",
        "description": "Google BigQuery",
    },
    "redshift": {
        "check_command": "psql --version",
        "install_command": "pip install dbt-redshift",
        "connection_format": "redshift://user:password@host:port/database",
        "description": "Amazon Redshift",
    },
    "databricks": {
        "check_command": "databricks --version",
        "install_command": "pip install dbt-databricks",
        "connection_format": "databricks://host:port/database",
        "description": "Databricks",
    },
}


def make_dbt_connection_error(
    connection_string: str | None = None,
    adapter_type: str | None = None,
    error_details: str | None = None,
) -> ActionableError:
    """Create an ActionableError for a dbt database connection error.

    This function builds an error message with database-specific troubleshooting
    steps and recovery suggestions.

    Args:
        connection_string: The connection string that failed (optional).
        adapter_type: The database adapter type (e.g., "duckdb", "postgres").
            If not provided, attempts to infer from connection_string.
        error_details: Additional error details from the exception (optional).

    Returns:
        An ActionableError with database-specific troubleshooting suggestions.

    Example:
        >>> error = make_dbt_connection_error("analytics.duckdb", adapter_type="duckdb")
        >>> error.error_type
        <ErrorType.DBT_CONNECTION_ERROR: 'dbt_connection_error'>
        >>> "duckdb" in str(error.suggestions).lower()
        True
    """
    # Try to infer adapter type from connection string
    inferred_adapter = adapter_type
    if not inferred_adapter and connection_string:
        conn_lower = connection_string.lower()
        if conn_lower.endswith(".duckdb") or conn_lower.endswith(".db"):
            inferred_adapter = "duckdb"
        elif conn_lower.startswith("postgresql://") or conn_lower.startswith("postgres://"):
            inferred_adapter = "postgres"
        elif conn_lower.startswith("redshift://"):
            inferred_adapter = "redshift"
        elif "snowflake" in conn_lower:
            inferred_adapter = "snowflake"
        elif "bigquery" in conn_lower or "bq://" in conn_lower:
            inferred_adapter = "bigquery"
        elif "databricks" in conn_lower:
            inferred_adapter = "databricks"

    # Build the main message
    if connection_string:
        message = f"Failed to connect to database: '{connection_string}'"
    else:
        message = "Failed to connect to database"

    # Build suggestions based on adapter type
    suggestions: list[str] = []

    if inferred_adapter:
        adapter_info = DBT_DATABASE_ADAPTERS.get(inferred_adapter.lower())
        if adapter_info:
            suggestions.append(f"Ensure {adapter_info['description']} is installed and running")
            suggestions.append(f"Verify connection string format: {adapter_info['connection_format']}")

    # Add general suggestions
    suggestions.extend([
        "Check if the database server is running and accessible",
        "Verify credentials (username/password) are correct",
        "Ensure network connectivity to the database host",
    ])

    # Add adapter-specific suggestions
    if inferred_adapter == "duckdb" and connection_string:
        # DuckDB is file-based, check if file exists
        suggestions.insert(0, f"Check if the database file exists: {connection_string}")
        suggestions.append("DuckDB will create a new file if it doesn't exist with write permissions")
    elif inferred_adapter in ("postgres", "postgresql"):
        suggestions.append("Check PostgreSQL is running: 'pg_isready'")
        suggestions.append("Verify the database and schema exist")
    elif inferred_adapter == "snowflake":
        suggestions.append("Verify your Snowflake account, warehouse, and role settings")
        suggestions.append("Check that your IP is whitelisted if using network policies")
    elif inferred_adapter == "bigquery":
        suggestions.append("Ensure GOOGLE_APPLICATION_CREDENTIALS is set")
        suggestions.append("Verify project and dataset permissions")

    # Add error-specific suggestions based on error_details
    if error_details:
        error_lower = error_details.lower()
        if "permission" in error_lower or "access denied" in error_lower:
            suggestions.insert(0, "Check database user permissions")
        elif "timeout" in error_lower:
            suggestions.insert(0, "Connection timed out - check network and firewall settings")
        elif "authentication" in error_lower or "password" in error_lower:
            suggestions.insert(0, "Authentication failed - verify username and password")
        elif "not found" in error_lower or "does not exist" in error_lower:
            suggestions.insert(0, "Database or schema does not exist - verify the name")
        elif "ssl" in error_lower or "certificate" in error_lower:
            suggestions.insert(0, "SSL/TLS issue - check certificate configuration")

    # Build recovery commands
    recovery_commands = []

    if inferred_adapter:
        adapter_info = DBT_DATABASE_ADAPTERS.get(inferred_adapter.lower())
        if adapter_info:
            recovery_commands.append(adapter_info["check_command"])
            recovery_commands.append(f"# Install adapter if needed:")
            recovery_commands.append(adapter_info["install_command"])

    if inferred_adapter == "duckdb" and connection_string:
        recovery_commands.insert(0, f"ls -la {connection_string}")
    elif inferred_adapter in ("postgres", "postgresql"):
        recovery_commands.insert(0, "pg_isready")

    recovery_commands.extend([
        "# Check dbt connection:",
        "dbt debug",
        "# View profiles:",
        "cat ~/.dbt/profiles.yml",
    ])

    # Build context
    context: dict[str, str] = {}
    if connection_string:
        context["connection_string"] = connection_string
    if inferred_adapter:
        context["adapter_type"] = inferred_adapter
    if error_details:
        # Truncate long error details
        context["error_details"] = error_details[:200] if len(error_details) > 200 else error_details

    return ActionableError(
        error_type=ErrorType.DBT_CONNECTION_ERROR,
        message=message,
        suggestions=suggestions,
        recovery_commands=recovery_commands,
        context=context,
    )


def make_dbt_model_not_found_error(
    model_name: str,
    available_models: Sequence[str] | None = None,
    project_dir: str | None = None,
    n: int = DEFAULT_MAX_SUGGESTIONS,
    cutoff: float = DEFAULT_SIMILARITY_THRESHOLD,
) -> ActionableError:
    """Create an ActionableError for a dbt model not found error.

    This function builds an error message with similar model suggestions
    based on fuzzy matching against available models in the dbt project.

    Args:
        model_name: The model name that was not found.
        available_models: List of available model names in the project.
            If not provided, no similar suggestions will be given.
        project_dir: The dbt project directory (for context).
        n: Maximum number of similar models to suggest. Defaults to 3.
        cutoff: Similarity threshold (0.0 to 1.0). Defaults to 0.6.

    Returns:
        An ActionableError with suggestions for similar models and
        troubleshooting steps.

    Example:
        >>> error = make_dbt_model_not_found_error("stg_ordes", ["stg_orders", "stg_customers"])
        >>> error.error_type
        <ErrorType.DBT_MODEL_NOT_FOUND: 'dbt_model_not_found'>
        >>> "stg_orders" in error.related_items
        True
    """
    model_str = model_name.strip()

    # Find similar models
    similar: list[str] = []
    if available_models:
        similar = suggest_values(model_str, available_models, n=n, cutoff=cutoff)

    # Build the main message
    message = f"dbt model '{model_str}' not found"

    # Build suggestions
    suggestions = [
        "Check if the model name is spelled correctly",
    ]

    # Mention similar models
    if similar:
        if len(similar) == 1:
            suggestions.insert(0, f"Did you mean '{similar[0]}'?")
        else:
            suggestions.insert(0, f"Similar models: {', '.join(similar)}")

    # Add dbt-specific suggestions
    suggestions.extend([
        "Ensure the model file exists in the models/ directory",
        "Check if the model is defined in a schema.yml file",
        "Model files should be named <model_name>.sql",
    ])

    # If few available models, list them all
    if available_models:
        if len(available_models) <= 10:
            formatted_models = ", ".join(sorted(available_models))
            suggestions.append(f"Available models: {formatted_models}")
        else:
            suggestions.append(
                f"Use 'dbt list' to see all {len(available_models)} available models"
            )
    else:
        suggestions.append("Run 'dbt list' to see all available models in the project")

    # Build recovery commands
    recovery_commands = [
        "dbt list --resource-type model",
        f"# Find model file:",
        f"find models/ -name '*{model_str}*' -type f 2>/dev/null",
    ]

    if similar:
        # Suggest running the similar model
        recovery_commands.insert(0, f"dbt run --select {similar[0]}")

    recovery_commands.extend([
        "# Compile to check for errors:",
        "dbt compile",
        "# Check model graph:",
        "dbt docs generate && dbt docs serve",
    ])

    # Build context
    context = {
        "model_name": model_str,
    }
    if project_dir:
        context["project_dir"] = project_dir
    if available_models:
        context["available_count"] = str(len(available_models))

    return ActionableError(
        error_type=ErrorType.DBT_MODEL_NOT_FOUND,
        message=message,
        suggestions=suggestions,
        recovery_commands=recovery_commands,
        related_items=similar,
        context=context,
    )


# Common dbt command error patterns and their solutions
DBT_COMMAND_ERROR_PATTERNS: dict[str, dict[str, list[str]]] = {
    "compilation error": {
        "suggestions": [
            "Check for syntax errors in your model SQL",
            "Verify all referenced models and sources exist",
            "Ensure Jinja macros are correctly formatted",
        ],
        "recovery_commands": [
            "dbt compile --select <model>",
            "dbt parse",
        ],
    },
    "database error": {
        "suggestions": [
            "Check your database connection settings",
            "Verify the query is valid for your database",
            "Ensure referenced tables/views exist",
        ],
        "recovery_commands": [
            "dbt debug",
        ],
    },
    "dependency error": {
        "suggestions": [
            "Check if upstream models are built",
            "Verify ref() and source() references are correct",
            "Run upstream dependencies first",
        ],
        "recovery_commands": [
            "dbt run --select +<model>",
            "dbt list --select +<model>",
        ],
    },
    "test failed": {
        "suggestions": [
            "Review test results for specific failures",
            "Check data quality in source tables",
            "Verify test definitions in schema.yml",
        ],
        "recovery_commands": [
            "dbt test --select <model>",
            "dbt show --select <model> --limit 10",
        ],
    },
    "runtime error": {
        "suggestions": [
            "Check for resource constraints (memory, disk)",
            "Verify database permissions",
            "Review query complexity",
        ],
        "recovery_commands": [
            "dbt run --select <model> --full-refresh",
        ],
    },
    "profile not found": {
        "suggestions": [
            "Check profiles.yml exists in ~/.dbt/",
            "Verify the profile name matches dbt_project.yml",
            "Ensure correct target is specified",
        ],
        "recovery_commands": [
            "cat ~/.dbt/profiles.yml",
            "cat dbt_project.yml | grep profile",
            "dbt debug",
        ],
    },
    "package not found": {
        "suggestions": [
            "Run 'dbt deps' to install packages",
            "Check packages.yml for correct package versions",
            "Verify package names and git URLs",
        ],
        "recovery_commands": [
            "dbt deps",
            "cat packages.yml",
        ],
    },
}


def make_dbt_command_error(
    command: str,
    error_output: str | None = None,
    exit_code: int | None = None,
    model_name: str | None = None,
) -> ActionableError:
    """Create an ActionableError for a dbt command execution error.

    This function analyzes the error output and provides targeted
    troubleshooting suggestions based on common dbt error patterns.

    Args:
        command: The dbt command that failed (e.g., "dbt run", "dbt test").
        error_output: The error output from the command (stderr/stdout).
        exit_code: The exit code from the command (optional).
        model_name: The specific model being operated on (optional).

    Returns:
        An ActionableError with dbt-specific troubleshooting suggestions.

    Example:
        >>> error = make_dbt_command_error("dbt run", "Compilation Error", model_name="stg_orders")
        >>> error.error_type
        <ErrorType.DBT_COMMAND_ERROR: 'dbt_command_error'>
        >>> "compile" in str(error.recovery_commands).lower()
        True
    """
    # Build the main message
    if model_name:
        message = f"dbt command '{command}' failed for model '{model_name}'"
    else:
        message = f"dbt command '{command}' failed"

    if exit_code is not None and exit_code != 0:
        message += f" (exit code: {exit_code})"

    # Analyze error output to determine specific suggestions
    suggestions: list[str] = []
    recovery_commands: list[str] = []

    if error_output:
        error_lower = error_output.lower()

        # Check for known error patterns
        for pattern, info in DBT_COMMAND_ERROR_PATTERNS.items():
            if pattern in error_lower:
                suggestions.extend(info["suggestions"])
                for cmd in info["recovery_commands"]:
                    # Replace <model> placeholder with actual model name if available
                    if model_name:
                        cmd = cmd.replace("<model>", model_name)
                    recovery_commands.append(cmd)
                break

        # Additional pattern matching
        if "permission denied" in error_lower:
            suggestions.insert(0, "Check database user permissions")
            suggestions.append("Ensure you have write access to the target schema")
        elif "timeout" in error_lower:
            suggestions.insert(0, "Command timed out - try with a longer timeout or smaller selection")
            recovery_commands.insert(0, "dbt run --select <model> --threads 1")
        elif "out of memory" in error_lower or "memory" in error_lower:
            suggestions.insert(0, "Query ran out of memory - try optimizing or reducing data volume")
            suggestions.append("Consider using incremental models for large datasets")
        elif "relation" in error_lower and "does not exist" in error_lower:
            suggestions.insert(0, "Referenced table or view does not exist")
            suggestions.append("Run upstream dependencies first")
            if model_name:
                recovery_commands.insert(0, f"dbt run --select +{model_name}")
        elif "column" in error_lower and ("not found" in error_lower or "does not exist" in error_lower):
            suggestions.insert(0, "Referenced column does not exist - check column names")
            suggestions.append("Verify source data schema matches your model")
        elif "freshness" in error_lower:
            suggestions.insert(0, "Source freshness check failed")
            suggestions.append("Verify source data is being updated as expected")
            recovery_commands.insert(0, "dbt source freshness")
        elif "seed" in error_lower:
            suggestions.insert(0, "Seed operation failed - check CSV file format")
            recovery_commands.insert(0, "dbt seed --full-refresh")
        elif "snapshot" in error_lower:
            suggestions.insert(0, "Snapshot operation failed - check strategy and unique_key")
            recovery_commands.insert(0, "dbt snapshot")

    # Add general suggestions if none were added from patterns
    if not suggestions:
        suggestions = [
            "Check the dbt logs for detailed error messages",
            "Verify your dbt project configuration",
            "Ensure all dependencies are up to date",
        ]

    # Add general recovery commands
    if not recovery_commands:
        recovery_commands = [
            "# View detailed logs:",
            "cat logs/dbt.log | tail -100",
            "# Debug connection:",
            "dbt debug",
        ]

    # Always add these useful commands at the end
    recovery_commands.extend([
        "# Parse project for errors:",
        "dbt parse",
        "# List all resources:",
        "dbt list",
    ])

    # Build context
    context: dict[str, str] = {
        "command": command,
    }
    if model_name:
        context["model"] = model_name
    if exit_code is not None:
        context["exit_code"] = str(exit_code)
    if error_output:
        # Truncate long error output
        truncated = error_output[:300] if len(error_output) > 300 else error_output
        # Clean up for display
        truncated = truncated.replace("\n", " ").strip()
        context["error_summary"] = truncated

    return ActionableError(
        error_type=ErrorType.DBT_COMMAND_ERROR,
        message=message,
        suggestions=suggestions,
        recovery_commands=recovery_commands,
        context=context,
    )
