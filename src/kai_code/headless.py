from __future__ import annotations

from typing import Any

from . import cli


def handle_headless_command(argv: list[str], model: str | None = None, skills_directory: str | None = None) -> int:
    """TypeScript compatibility wrapper.

    In `letta-code`, this parses CLI argv and prints results.
    Here we forward to the `kai` CLI implementation.
    """
    args = list(argv)
    # Drop interpreter + script if present.
    if args and (args[0].endswith("python") or args[0].endswith("python3")):
        args = args[1:]
    if args and (args[0].endswith("kai") or args[0].endswith("kai.py")):
        args = args[1:]

    # Inject defaults if caller provided them and user didn't.
    if model and "--model" not in args and "-m" not in args:
        args = ["--model", model, *args]
    if skills_directory and "--skills" not in args:
        args = ["--skills", skills_directory, *args]
    return cli.main(args)


def run_headless(argv: list[str], **kwargs: Any) -> int:
    """Alias for handle_headless_command (Python naming convenience)."""
    return handle_headless_command(argv, **kwargs)


# TypeScript-compat alias
handleHeadlessCommand = handle_headless_command
