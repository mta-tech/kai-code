"""kai-dbt CLI - Data Engineering Agent Entry Point."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import TYPE_CHECKING

__all__ = ["parse_args", "main", "cli_main"]


def parse_args(args: list[str] | None = None) -> argparse.Namespace:
    """Parse command line arguments for kai-dbt CLI.

    Args:
        args: Optional list of arguments (defaults to sys.argv[1:])

    Returns:
        Parsed namespace with CLI options
    """
    parser = argparse.ArgumentParser(
        prog="kai-dbt",
        description="Kai dbt Engineer - AI-powered data engineering assistant",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "prompt",
        nargs="*",
        help="Initial prompt to send to the agent (optional)",
    )

    parser.add_argument(
        "-y", "--yes",
        action="store_true",
        dest="auto_approve",
        help="Auto-approve all tool actions (dangerous, use with caution)",
    )

    parser.add_argument(
        "--no-splash",
        action="store_true",
        help="Skip the startup banner",
    )

    # Database connection
    parser.add_argument(
        "--db",
        type=str,
        default=None,
        help="Database connection string (e.g., analytics.duckdb, postgresql://...)",
    )

    # dbt configuration
    parser.add_argument(
        "--profile",
        type=str,
        default=None,
        help="dbt profile name to use",
    )

    parser.add_argument(
        "--target",
        type=str,
        default=None,
        help="dbt target environment",
    )

    parser.add_argument(
        "--project-dir",
        type=str,
        default=None,
        help="Path to dbt project directory (auto-detected if not specified)",
    )

    parser.add_argument(
        "--docs-dir",
        type=str,
        default=None,
        help="Path to dbt documentation directory",
    )

    parser.add_argument(
        "--schema",
        type=str,
        default=None,
        help="Default schema to explore",
    )

    # Environment configuration
    parser.add_argument(
        "--env",
        type=str,
        default="default",
        help="Configuration environment (from .kai/dbt.yaml)",
    )

    parser.add_argument(
        "-v", "--version",
        action="store_true",
        help="Show version information",
    )

    parser.add_argument(
        "--help-commands",
        action="store_true",
        help="Show available slash commands",
    )

    return parser.parse_args(args)


def main(args: list[str] | None = None) -> int:
    """Main entry point for kai-dbt CLI.

    Args:
        args: Optional list of command line arguments

    Returns:
        Exit code (0 for success)
    """
    parsed = parse_args(args)

    # Handle --version
    if parsed.version:
        try:
            from kai_code import __version__
            print(f"kai-dbt {__version__}")
        except ImportError:
            print("kai-dbt (development)")
        return 0

    # TODO: Implement main CLI loop
    print("kai-dbt CLI - implementation in progress")
    return 0


def cli_main() -> None:
    """CLI entry point that handles exit codes properly."""
    sys.exit(main())


if __name__ == "__main__":
    cli_main()
