"""kai-seeknal CLI - Data Engineering & Data Science Agent Entry Point."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from rich.console import Console

from kai_code.rich_config import COLORS
from kai_code.errors import ActionableError, ErrorType, render_error
from kai_code.error_suggestions import make_model_not_available_error

if TYPE_CHECKING:
    from .agent import SeeknalAgent

console = Console(highlight=False)

__all__ = ["parse_args", "main", "cli_main"]


# ASCII banner for kai-seeknal
SEEKNAL_ASCII_BANNER = r"""
[bold cyan]
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║   [bold white]Kai Seeknal[/bold white] - Data Engineering & Data Science Agent  ║
║                                                               ║
║   [dim]Powered by Seeknal: Feature Store & Data Pipelines[/dim]        ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
[/bold cyan]
"""


def parse_args(args: list[str] | None = None) -> argparse.Namespace:
    """Parse command line arguments for kai-seeknal CLI.

    Args:
        args: Optional list of arguments (defaults to sys.argv[1:])

    Returns:
        Parsed namespace with CLI options
    """
    parser = argparse.ArgumentParser(
        prog="kai-seeknal",
        description="Kai Seeknal - AI-powered data engineering and data science assistant",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "prompt",
        nargs="*",
        help="Initial prompt to send to the agent (optional)",
    )

    parser.add_argument(
        "-y",
        "--yes",
        action="store_true",
        dest="auto_approve",
        help="Auto-approve all tool actions (dangerous, use with caution)",
    )

    parser.add_argument(
        "--no-splash",
        action="store_true",
        help="Skip the startup banner",
    )

    # Seeknal configuration
    parser.add_argument(
        "--seeknal-path",
        type=str,
        default=None,
        help="Path to Seeknal library (defaults to ~/project/mta/signal)",
    )

    # Environment configuration
    parser.add_argument(
        "-m",
        "--model",
        type=str,
        default=None,
        help="Model to use (e.g., sonnet-4.5, gpt-4o, gemini-2.0-flash)",
    )

    parser.add_argument(
        "-v",
        "--version",
        action="store_true",
        help="Show version information",
    )

    parser.add_argument(
        "--help-commands",
        action="store_true",
        help="Show available slash commands",
    )

    # Ralph autonomous loop flags
    parser.add_argument(
        "--ralph",
        action="store_true",
        help="Enable Ralph autonomous loop mode",
    )

    parser.add_argument(
        "--ralph-promise",
        "--completion-promise",
        dest="ralph_promise",
        type=str,
        default=None,
        help="Exact string to detect completion (e.g., TESTS_PASS)",
    )

    parser.add_argument(
        "--ralph-max-iterations",
        type=int,
        default=50,
        help="Maximum iterations before stopping (default: 50)",
    )

    parser.add_argument(
        "--ralph-timeout",
        type=int,
        default=None,
        help="Wall-clock timeout in seconds (optional)",
    )

    parser.add_argument(
        "--ralph-token-limit",
        type=int,
        default=500_000,
        help="Maximum total tokens to use (default: 500000)",
    )

    return parser.parse_args(args)


def create_startup_info(config: argparse.Namespace) -> str:
    """Create startup information string.

    Args:
        config: Parsed CLI configuration

    Returns:
        Formatted startup info
    """
    from kai_code.model import get_default_model

    model = config.model or get_default_model()

    info_parts = [
        f"[{COLORS['accent']}]Model:[/{COLORS['accent']}] {model}",
    ]

    if config.seeknal_path:
        info_parts.append(
            f"[{COLORS['accent']}]Seeknal:[/{COLORS['accent']}] {config.seeknal_path}"
        )
    else:
        default_path = Path.home() / "project" / "mta" / "signal"
        info_parts.append(
            f"[{COLORS['accent']}]Seeknal:[/{COLORS['accent']}] {default_path} (default)"
        )

    if config.auto_approve:
        info_parts.append(
            f"[{COLORS['warning']}]⚠ Auto-approve mode enabled[/]"
        )

    return " | ".join(info_parts)


def show_version() -> None:
    """Show version information."""
    console.print(f"[bold]kai-seeknal[/bold] version [cyan]1.0.0[/cyan]")
    console.print("Seeknal integration for Kai Code")
    sys.exit(0)


def show_help_commands() -> None:
    """Show available slash commands."""
    from kai_code.rich_commands import get_all_commands

    commands = get_all_commands()

    console.print("\n[bold]Available Slash Commands:[/bold]\n")

    for name, cmd in commands.items():
        console.print(f"  [cyan]{name}[/cyan] - {cmd.description}")

    console.print("\n[dim]Type '/' followed by a command name to use it.[/dim]\n")
    sys.exit(0)


def create_agent(
    root_dir: Path,
    config: argparse.Namespace,
) -> "SeeknalAgent":
    """Create and initialize the SeeknalAgent.

    Args:
        root_dir: Project root directory
        config: Parsed CLI configuration

    Returns:
        Initialized SeeknalAgent instance

    Raises:
        ActionableError: If agent creation fails
    """
    try:
        from kai_code.agents.seeknal import SeeknalAgent

        # Resolve Seeknal path
        seeknal_path = config.seeknal_path
        if not seeknal_path:
            seeknal_path = Path.home() / "project" / "mta" / "signal"

        # Create agent
        agent = SeeknalAgent(
            root_dir=root_dir,
            model=config.model,
            seeknal_path=seeknal_path,
            yolo=config.auto_approve,
        )

        return agent

    except Exception as e:
        raise ActionableError(
            error_type=ErrorType.INITIALIZATION,
            message=f"Failed to initialize SeeknalAgent: {e}",
            suggestions=[
                "Check that Seeknal library is installed",
                f"Verify Seeknal path: {config.seeknal_path or '~/project/mta/signal'}",
                "Ensure Python 3.11+ is available",
            ],
            original_error=e,
        )


def simple_cli(agent: "SeeknalAgent", prompt: str) -> str:
    """Run a simple non-interactive CLI session.

    Args:
        agent: SeeknalAgent instance
        prompt: User prompt

    Returns:
        Agent output
    """
    result = agent.run(prompt)
    return result.output


def main(
    args: list[str] | None = None,
    root_dir: Path | None = None,
) -> None:
    """Main entry point for kai-seeknal CLI.

    Args:
        args: Optional list of arguments (defaults to sys.argv[1:])
        root_dir: Optional root directory (defaults to current working directory)
    """
    # Parse arguments
    config = parse_args(args)

    # Handle version flag
    if config.version:
        show_version()

    # Handle help commands flag
    if config.help_commands:
        show_help_commands()

    # Determine root directory
    if root_dir is None:
        root_dir = Path.cwd()
    else:
        root_dir = Path(root_dir)

    # Show splash screen
    if not config.no_splash:
        console.print(SEEKNAL_ASCII_BANNER)
        startup_info = create_startup_info(config)
        console.print(f"{startup_info}\n")
        console.print("[dim]Type 'help' for available commands or 'exit' to quit.[/dim]\n")

    try:
        # Create agent
        agent = create_agent(root_dir, config)

        # Configure Ralph loop if enabled
        if config.ralph:
            from kai_code.ralph_loop import RalphLoopConfig

            ralph_config = RalphLoopConfig(
                enabled=True,
                promise=config.ralph_promise,
                max_iterations=config.ralph_max_iterations,
                timeout=config.ralph_timeout,
                token_limit=config.ralph_token_limit,
            )
            agent.ralph_manager.configure(ralph_config)

        # Check if we have an initial prompt
        if config.prompt:
            # Non-interactive mode with prompt
            prompt_text = " ".join(config.prompt)
            output = simple_cli(agent, prompt_text)
            console.print(output)

            # Save session
            agent.save()
        else:
            # Launch interactive CLI
            from kai_code.rich_main import launch_interactive_cli

            launch_interactive_cli(agent, config)

    except ActionableError as e:
        render_error(e)
        sys.exit(1)
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user[/yellow]")
        sys.exit(130)
    except Exception as e:
        render_error(
            ActionableError(
                error_type=ErrorType.UNKNOWN,
                message=f"Unexpected error: {e}",
                suggestions=[
                    "Check the error message above",
                    "Try running with --help for usage information",
                ],
                original_error=e,
            )
        )
        sys.exit(1)


def cli_main() -> None:
    """CLI entry point (used by setuptools console_scripts)."""
    main()
