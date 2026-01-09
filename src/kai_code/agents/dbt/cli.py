"""kai-dbt CLI - Data Engineering Agent Entry Point."""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from rich.console import Console

from .banner import DBT_ASCII_BANNER, create_startup_info, format_schema_summary
from .config import DbtCliConfig, load_config, find_dbt_project
from .commands import DbtCommandHandler
from kai_code.rich_config import COLORS
from kai_code.errors import ActionableError, ErrorType, render_error
from kai_code.error_suggestions import (
    make_dbt_connection_error,
    make_model_not_available_error,
    PROVIDER_API_KEY_INSTRUCTIONS,
)

if TYPE_CHECKING:
    from .agent import DbtAgent
    from .adapters import DatabaseAdapter
    from langgraph.graph.state import CompiledStateGraph

console = Console(highlight=False)

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
        "-m",
        "--model",
        type=str,
        default=None,
        help="Model to use (e.g., sonnet-4, gpt-4o, gemini-2.0-flash)",
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


def _show_help_commands() -> None:
    """Show available dbt slash commands."""
    console.print("\n[bold cyan]dbt Slash Commands:[/bold cyan]\n")
    commands = [
        ("/schema", "Show database schema summary"),
        ("/model <name>", "Show model details and columns"),
        ("/dbt run [model]", "Run dbt models"),
        ("/dbt test [model]", "Run dbt tests"),
        ("/dbt compile [model]", "Compile dbt models"),
        ("/dbt list", "List dbt resources"),
        ("/dbt show <model>", "Preview model output"),
        ("/brainstorm [topic]", "Start a design brainstorm session"),
        ("/help", "Show this help"),
        ("/exit", "Exit kai-dbt"),
    ]
    for cmd, desc in commands:
        console.print(f"  [cyan]{cmd:<25}[/cyan] {desc}")
    console.print()


def _show_startup_banner(
    project_name: str | None = None,
    adapter: "DatabaseAdapter | None" = None,
    profile: str | None = None,
    target: str | None = None,
    no_splash: bool = False,
) -> None:
    """Display startup banner and schema summary.

    Args:
        project_name: dbt project name.
        adapter: Database adapter for schema info.
        profile: dbt profile name.
        target: dbt target environment.
        no_splash: If True, skip the banner.
    """
    if no_splash:
        return

    # Show ASCII banner (same color scheme as kai-code)
    console.print(DBT_ASCII_BANNER, style=f"bold {COLORS['primary']}")

    # Get database info
    db_connected = adapter is not None
    db_name = None
    table_count = None
    tables = []

    if adapter:
        try:
            tables = adapter.get_tables()
            table_count = len(tables)
            # Get db name from adapter (varies by type)
            if hasattr(adapter, "database_path"):
                db_name = str(adapter.database_path)
            elif hasattr(adapter, "_connection_string"):
                db_name = adapter._connection_string.split("/")[-1].split("?")[0]
        except Exception:
            pass

    # Show startup info
    info = create_startup_info(
        db_connected=db_connected,
        db_name=db_name,
        table_count=table_count,
        project_name=project_name,
        profile=profile,
        target=target,
    )
    console.print(info, style="dim")

    # Show schema summary table if connected
    if tables:
        console.print()
        table_data = [
            {
                "name": t.name,
                "column_count": t.column_count,
                "row_count": t.row_count,
            }
            for t in tables[:10]  # Limit to 10 tables
        ]
        console.print(format_schema_summary(table_data))
        if len(tables) > 10:
            console.print(f"  ... and {len(tables) - 10} more tables", style="dim")

    console.print()
    console.print("Type /help for commands, Ctrl+C twice to exit.", style="dim")
    console.print()


def _create_dbt_agent(
    project_dir: Path,
    db_connection: str | None = None,
    profile: str | None = None,
    target: str | None = None,
    yolo: bool = False,
    model: str | None = None,
) -> tuple["DbtAgent", "CompiledStateGraph"]:
    """Create DbtAgent instance.

    Args:
        project_dir: dbt project directory.
        db_connection: Database connection string.
        profile: dbt profile name.
        target: dbt target.
        yolo: Auto-approve mode (DEPRECATED - use session_state.auto_approve instead).
        model: Model name to use (e.g., sonnet-4, gpt-4o).

    Returns:
        Tuple of (DbtAgent, compiled graph).
    """
    from .agent import DbtAgent
    from kai_code.model import get_default_model, resolve_model

    # Get model - use provided or default
    if model:
        model_string = resolve_model(model)
    else:
        default_model = get_default_model()
        model_string = resolve_model(default_model)

    # Create agent with HITL enabled (yolo=False)
    # Auto-approve is controlled at runtime via session_state.auto_approve
    agent = DbtAgent(
        root_dir=project_dir,
        model=model_string,
        db_connection=db_connection,
        dbt_project_dir=project_dir,
        yolo=False,  # Always create with HITL enabled
    )

    # Build graph
    graph = agent._build_graph()

    return agent, graph


async def dbt_cli_loop(
    agent: "DbtAgent",
    graph: "CompiledStateGraph",
    initial_prompt: str | None = None,
    auto_approve: bool = False,
) -> None:
    """Main CLI loop for kai-dbt.

    Args:
        agent: DbtAgent instance.
        graph: Compiled LangGraph.
        initial_prompt: Optional initial prompt.
        auto_approve: Auto-approve mode.
    """
    from kai_code.rich_execution import execute_task
    from kai_code.rich_config import SessionState
    from kai_code.cli_ui import TokenTracker
    from kai_code.rich_input import ImageTracker, create_prompt_session

    command_handler = DbtCommandHandler(agent)
    session_state = SessionState(auto_approve=auto_approve)
    token_tracker = TokenTracker()
    image_tracker = ImageTracker()

    prompt_session = create_prompt_session(
        "kai-dbt", session_state, image_tracker=image_tracker
    )

    # Handle initial prompt
    if initial_prompt:
        try:
            await execute_task(
                initial_prompt,
                graph,
                "kai-dbt",
                session_state,
                token_tracker=token_tracker,
                backend=agent.backend,
                image_tracker=image_tracker,
            )
        except Exception as e:
            error_str = str(e).lower()
            suggestions = [
                "Check if the prompt is valid for dbt operations",
                "Verify your database connection is working",
            ]

            # Add context-specific suggestions based on error content
            if "dbt" in error_str:
                suggestions.append("Run 'dbt debug' to verify dbt configuration")
            if "connection" in error_str or "database" in error_str:
                suggestions.append("Check your database connection settings")
            if "api" in error_str or "key" in error_str:
                suggestions.append("Verify your API key is set correctly")

            error = ActionableError(
                error_type=ErrorType.COMMAND_EXECUTION_ERROR,
                message=f"Error executing prompt: {e}",
                suggestions=suggestions,
                recovery_commands=[
                    "dbt debug",
                    "/help",
                ],
                severity="warning",
                context={
                    "prompt": initial_prompt[:100] if len(initial_prompt) > 100 else initial_prompt,
                    "error_details": str(e),
                },
            )
            render_error(error, console=console)

    # Main loop
    while True:
        try:
            user_input = await asyncio.to_thread(
                prompt_session.prompt,
                "kai-dbt> ",
            )
            user_input = user_input.strip()

            if not user_input:
                continue

            if user_input.startswith("/"):
                if user_input == "/exit" or user_input == "/quit":
                    console.print("Goodbye!", style="dim")
                    break

                result = command_handler.handle(user_input)
                if result:
                    console.print(result)
                    continue

                from kai_code.rich_commands import handle_command

                fallback_result = handle_command(user_input, agent, token_tracker)
                if fallback_result == "exit":
                    console.print("Goodbye!", style="dim")
                    break
                if fallback_result == "model_select":
                    # Handle interactive model selection
                    from kai_code.model_selector import show_model_selector, format_current_model, get_available_models

                    selected = show_model_selector(current_model=session_state.model)
                    if selected and selected.handle != session_state.model:
                        console.print(f"[dim]Switching to model: {selected.id}[/dim]")
                        try:
                            project_dir = getattr(agent, 'dbt_project_dir', None) or Path.cwd()
                            db_conn = getattr(agent, '_db_connection', None)
                            new_agent, new_graph = _create_dbt_agent(
                                project_dir=project_dir,
                                db_connection=db_conn,
                                model=selected.id,
                            )
                            # Update references for next iteration
                            agent = new_agent
                            graph = new_graph
                            session_state.model = selected.handle
                            console.print(f"[green]Model switched to: {format_current_model(selected.handle)}[/green]")
                        except Exception as e:
                            # Get available models for suggestions
                            available_models = get_available_models()
                            available_model_ids = [m.id for m in available_models]

                            error = make_model_not_available_error(
                                model=selected.id,
                                available_models=available_model_ids,
                            )
                            # Override the message to be more specific about the switch failure
                            error = ActionableError(
                                error_type=ErrorType.MODEL_NOT_AVAILABLE,
                                message=f"Failed to switch to model '{selected.id}': {e}",
                                suggestions=error.suggestions,
                                recovery_commands=error.recovery_commands,
                                related_items=error.related_items,
                                severity="warning",
                                context={
                                    "requested_model": selected.id,
                                    "current_model": session_state.model or "none",
                                    "error_details": str(e),
                                },
                            )
                            render_error(error, console=console)
                    continue
                if fallback_result is None:
                    continue
                user_input = fallback_result

            # Handle bash commands (starting with !)
            if user_input.startswith("!"):
                from kai_code.rich_commands import execute_bash_command

                execute_bash_command(user_input)
                continue

            # Execute through agent
            try:
                await execute_task(
                    user_input,
                    graph,
                    "kai-dbt",
                    session_state,
                    token_tracker=token_tracker,
                    backend=agent.backend,
                    image_tracker=image_tracker,
                )
            except Exception as e:
                error_str = str(e).lower()
                suggestions = [
                    "Check if your request is valid for dbt operations",
                    "Try rephrasing your prompt",
                ]

                # Add context-specific suggestions based on error content
                if "dbt" in error_str:
                    suggestions.append("Run 'dbt debug' to verify dbt configuration")
                if "connection" in error_str or "database" in error_str:
                    suggestions.append("Check your database connection settings")
                if "model" in error_str:
                    suggestions.append("Verify the model name exists in your dbt project")
                if "api" in error_str or "key" in error_str or "auth" in error_str:
                    suggestions.append("Verify your API key is set correctly")
                if "timeout" in error_str:
                    suggestions.append("The request timed out - try again or simplify the task")

                error = ActionableError(
                    error_type=ErrorType.COMMAND_EXECUTION_ERROR,
                    message=f"Error executing task: {e}",
                    suggestions=suggestions,
                    recovery_commands=[
                        "dbt debug",
                        "/help",
                    ],
                    severity="warning",
                    context={
                        "user_input": user_input[:100] if len(user_input) > 100 else user_input,
                        "error_details": str(e),
                    },
                )
                render_error(error, console=console)

        except KeyboardInterrupt:
            console.print()
            continue
        except EOFError:
            console.print("\nGoodbye!", style="dim")
            break


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

            console.print(f"kai-dbt {__version__}")
        except ImportError:
            console.print("kai-dbt (development)")
        return 0

    # Handle --help-commands
    if parsed.help_commands:
        _show_help_commands()
        return 0

    # Load configuration
    project_dir_arg = Path(parsed.project_dir) if parsed.project_dir else None
    config = load_config(
        project_dir=project_dir_arg or Path.cwd(),
        env=parsed.env,
        cli_overrides={
            "connection": parsed.db,
            "profile": parsed.profile,
            "target": parsed.target,
            "docs_dir": parsed.docs_dir,
            "schema": parsed.schema,
        },
    )

    # Find dbt project
    search_dir = project_dir_arg or Path.cwd()
    project_info = find_dbt_project(search_dir)
    project_dir = project_info.project_dir if project_info else Path.cwd()
    project_name = project_info.project_name if project_info else None
    project_profile = project_info.profile if project_info else None

    # Use config values or project defaults
    profile = config.profile or project_profile
    target = config.target

    # Create agent
    agent = None
    graph = None
    try:
        agent, graph = _create_dbt_agent(
            project_dir=project_dir,
            db_connection=config.connection,
            profile=profile,
            target=target,
            model=parsed.model,
        )
    except Exception as e:
        # Warn and continue without db if connection failed
        if config.connection:
            # Use DBT-specific connection error
            conn_error = make_dbt_connection_error(
                connection_string=config.connection,
                error_details=str(e),
            )
            # Override severity to warning since we'll continue without DB
            conn_error = ActionableError(
                error_type=conn_error.error_type,
                message=conn_error.message,
                suggestions=conn_error.suggestions + ["Continuing without database connection..."],
                recovery_commands=conn_error.recovery_commands,
                related_items=conn_error.related_items,
                severity="warning",
                context=conn_error.context,
            )
            render_error(conn_error, console=console)

            try:
                agent, graph = _create_dbt_agent(
                    project_dir=project_dir,
                    db_connection=None,
                    profile=profile,
                    target=target,
                    model=parsed.model,
                )
            except Exception as e2:
                # Build agent creation error with context-specific suggestions
                error_str = str(e2).lower()
                suggestions = [
                    "Check if all dependencies are installed correctly",
                    "Verify your dbt project configuration",
                ]
                recovery_commands = ["dbt debug", "kai-dbt --help"]

                # Add context-specific suggestions
                if "api" in error_str or "key" in error_str or "auth" in error_str:
                    for provider, info in PROVIDER_API_KEY_INSTRUCTIONS.items():
                        if provider != "ollama" and info.get("env_var"):
                            suggestions.append(f"Set {info['env_var']} for {info['description']} models")
                            recovery_commands.append(f"export {info['env_var']}=your-key-here")
                            break
                if parsed.model:
                    suggestions.insert(0, f"Check if model '{parsed.model}' is available")

                error = ActionableError(
                    error_type=ErrorType.AGENT_CREATION_ERROR,
                    message=f"Failed to create dbt agent: {e2}",
                    suggestions=suggestions,
                    recovery_commands=recovery_commands,
                    severity="error",
                    context={
                        "requested_model": parsed.model or "default",
                        "project_dir": str(project_dir),
                        "error_details": str(e2),
                    },
                )
                render_error(error, console=console)
                return 1
        else:
            # Build agent creation error with context-specific suggestions
            error_str = str(e).lower()
            suggestions = [
                "Check if all dependencies are installed correctly",
                "Verify your dbt project configuration",
            ]
            recovery_commands = ["dbt debug", "kai-dbt --help"]

            # Add context-specific suggestions
            if "api" in error_str or "key" in error_str or "auth" in error_str:
                for provider, info in PROVIDER_API_KEY_INSTRUCTIONS.items():
                    if provider != "ollama" and info.get("env_var"):
                        suggestions.append(f"Set {info['env_var']} for {info['description']} models")
                        recovery_commands.append(f"export {info['env_var']}=your-key-here")
                        break
            if parsed.model:
                suggestions.insert(0, f"Check if model '{parsed.model}' is available")

            error = ActionableError(
                error_type=ErrorType.AGENT_CREATION_ERROR,
                message=f"Failed to create dbt agent: {e}",
                suggestions=suggestions,
                recovery_commands=recovery_commands,
                severity="error",
                context={
                    "requested_model": parsed.model or "default",
                    "project_dir": str(project_dir),
                    "error_details": str(e),
                },
            )
            render_error(error, console=console)
            return 1

    # Show banner
    _show_startup_banner(
        project_name=project_name,
        adapter=agent.adapter if agent else None,
        profile=profile,
        target=target,
        no_splash=parsed.no_splash,
    )

    # Get initial prompt
    initial_prompt = " ".join(parsed.prompt) if parsed.prompt else None

    # Handle Ralph mode - activate loop before running CLI
    if parsed.ralph:
        from kai_code.rich_config import COLORS

        # Start Ralph loop
        agent.ralph_manager.start_loop(
            prompt=initial_prompt or "Continue working on the dbt project",
            completion_promise=parsed.ralph_promise,
            max_iterations=parsed.ralph_max_iterations,
            timeout_seconds=parsed.ralph_timeout,
            token_limit=parsed.ralph_token_limit,
        )

        console.print()
        console.print("⟳ [bold cyan]Ralph autonomous loop activated![/bold cyan]")
        console.print(f"[dim]Prompt: {agent.ralph_manager.get_prompt()}[/dim]")
        if parsed.ralph_promise:
            console.print(f"[dim]Completion promise: {parsed.ralph_promise}[/dim]")
        console.print(f"[dim]Max iterations: {parsed.ralph_max_iterations}[/dim]")
        if parsed.ralph_timeout:
            console.print(f"[dim]Timeout: {parsed.ralph_timeout}s[/dim]")
        console.print(f"[dim]Token limit: {parsed.ralph_token_limit:,}[/dim]")
        console.print()

    # Run CLI
    try:
        asyncio.run(
            dbt_cli_loop(
                agent=agent,
                graph=graph,
                initial_prompt=initial_prompt,
                auto_approve=parsed.auto_approve,
            )
        )
        return 0
    except KeyboardInterrupt:
        console.print("\nGoodbye!", style="dim")
        return 0
    except Exception as e:
        error = ActionableError(
            error_type=ErrorType.INTERNAL_ERROR,
            message=f"Fatal error: {e}",
            suggestions=[
                "Check if all dependencies are installed correctly",
                "Verify your dbt project configuration is valid",
                "Try running with a different model using --model",
                "Check for any environment variable issues",
            ],
            recovery_commands=[
                "pip install -U kai-code",
                "dbt debug",
                "kai-dbt --help",
            ],
            severity="error",
            context={
                "error_type": type(e).__name__,
                "error_details": str(e),
            },
        )
        render_error(error, console=console)
        return 1
    finally:
        if agent and agent.adapter:
            try:
                agent.adapter.close()
            except Exception:
                pass


def cli_main() -> None:
    """CLI entry point that handles exit codes properly."""
    sys.exit(main())


if __name__ == "__main__":
    cli_main()
