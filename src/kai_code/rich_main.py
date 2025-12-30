"""Main entry point for the Rich CLI mode.

This module provides the main CLI loop that uses Rich for terminal rendering
and prompt-toolkit for interactive input.

Adapted from deepagents-cli for kai-code.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from kai_code.rich_config import (
    COLORS,
    KAI_CODE_ASCII,
    SessionState,
    console,
    rich_settings,
)
from kai_code.rich_commands import execute_bash_command, handle_command
from kai_code.rich_execution import execute_task
from kai_code.rich_input import (
    ImageTracker,
    create_prompt_session,
)
from kai_code.cli_ui import TokenTracker, show_interactive_help
from kai_code.tasks import get_task_manager
from kai_code.model_selector import show_model_selector, get_available_models, format_current_model
from kai_code.model import resolve_model, get_default_model, get_context_limit

if TYPE_CHECKING:
    from kai_code.agent import KaiAgent
    from langgraph.graph.state import CompiledStateGraph

__all__ = ["parse_args", "simple_cli", "main", "cli_main"]


def parse_args(args: list[str] | None = None) -> argparse.Namespace:
    """Parse command line arguments for the Rich CLI.

    Args:
        args: Optional list of arguments (defaults to sys.argv[1:])

    Returns:
        Parsed namespace with CLI options
    """
    parser = argparse.ArgumentParser(
        prog="kai",
        description="Kai Code - AI-powered coding assistant",
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

    parser.add_argument(
        "-i",
        "--interactive",
        action="store_true",
        help="Launch interactive CLI mode (default behavior)",
    )

    parser.add_argument(
        "--help-commands",
        action="store_true",
        help="Show available slash commands",
    )

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

    # Token indicator display flags
    token_group = parser.add_mutually_exclusive_group()
    token_group.add_argument(
        "--show-tokens",
        action="store_true",
        dest="show_tokens",
        default=None,
        help="Show token usage indicator in status bar",
    )
    token_group.add_argument(
        "--no-tokens",
        action="store_false",
        dest="show_tokens",
        help="Hide token usage indicator in status bar",
    )

    return parser.parse_args(args)


def _show_startup_banner(session_state: SessionState) -> None:
    """Display the startup banner and status information."""
    if session_state.no_splash:
        return

    # Display ASCII art banner
    console.print(KAI_CODE_ASCII, style=COLORS["primary"])

    # Show project status
    if rich_settings.has_project:
        console.print(f"Project: {rich_settings.project_root}", style="dim")
    else:
        console.print("No git project detected.", style="dim")

    # Show API status
    apis = []
    if rich_settings.has_anthropic:
        apis.append("Anthropic")
    if rich_settings.has_openai:
        apis.append("OpenAI")
    if rich_settings.has_google:
        apis.append("Google")
    if apis:
        console.print(f"APIs: {', '.join(apis)}", style="dim")

    # Show web tools status
    if rich_settings.has_tavily:
        console.print("Web search: Tavily enabled", style="dim")

    console.print()
    console.print("Type /help for commands, Ctrl+C twice to exit.", style="dim")
    console.print()


def _get_model_string(model_id: str | None = None) -> str:
    """Get the model string for KaiAgent.

    Args:
        model_id: Specific model ID to use, or None for default

    Returns:
        Model string in provider:model format
    """
    if model_id:
        resolved = resolve_model(model_id)
        if resolved:
            return resolved

    # Fall back to default
    default_model = get_default_model()
    return default_model


def _load_system_prompt() -> str:
    """Load system prompt from project and global configurations.

    Combines:
    1. Base kai-code system prompt
    2. Project-specific agent.md files (if in a project)
    3. User-level agent.md (if exists)

    Returns:
        Combined system prompt string
    """
    from kai_code.rich_config import _find_project_agent_md

    parts = []

    # Base system prompt
    base_prompt = """You are Kai, an expert AI coding assistant.

You help users with software development tasks including:
- Writing, reviewing, and debugging code
- Understanding codebases and explaining concepts
- Refactoring and optimizing code
- Creating tests and documentation
- Executing shell commands when needed

Always:
- Be concise and direct
- Prefer editing existing files over creating new ones
- Ask for clarification if requirements are unclear
- Consider edge cases and error handling
- Use appropriate coding conventions for the language
"""
    parts.append(base_prompt)

    # Load project-specific agent.md files
    if rich_settings.project_root:
        project_agent_files = _find_project_agent_md(rich_settings.project_root)
        for agent_file in project_agent_files:
            try:
                content = agent_file.read_text()
                if content.strip():
                    parts.append(
                        f"\n# Project Instructions ({agent_file.name})\n\n{content}"
                    )
            except (OSError, UnicodeDecodeError):
                pass

    # Load user-level agent.md
    user_agent_md = rich_settings.user_kai_dir / "agent.md"
    if user_agent_md.exists():
        try:
            content = user_agent_md.read_text()
            if content.strip():
                parts.append(f"\n# User Instructions\n\n{content}")
        except (OSError, UnicodeDecodeError):
            pass

    return "\n".join(parts)


def _create_kai_agent(
    *, yolo: bool = False, model: str | None = None
) -> tuple["KaiAgent", "CompiledStateGraph", str]:
    """Create the KaiAgent and return both the agent and its underlying graph.

    Args:
        yolo: If True, auto-approve all tool actions (no HITL prompts)
        model: Specific model ID to use, or None for default

    Returns:
        Tuple of (KaiAgent instance, compiled LangGraph for streaming, model_string)
    """
    from kai_code.agent import KaiAgent

    # Determine root directory (project root or cwd)
    root_dir = rich_settings.project_root or Path.cwd()

    # Get model string
    model_string = _get_model_string(model)

    # Get system prompt
    system_prompt = _load_system_prompt()

    # Create KaiAgent with proper configuration
    # yolo=True means auto-approve all, yolo=False means HITL enabled
    kai_agent = KaiAgent(
        root_dir=root_dir,
        model=model_string,
        yolo=yolo,
        system_prompt=system_prompt,
    )

    # Build and return the graph for streaming
    graph = kai_agent._build_graph()

    return kai_agent, graph, model_string


async def simple_cli(
    initial_prompt: str | None = None,
    session_state: SessionState | None = None,
) -> None:
    """Main interactive CLI loop using Rich and prompt-toolkit.

    Args:
        initial_prompt: Optional prompt to execute immediately on startup
        session_state: Session state (auto-approve, etc.) - created if not provided
    """
    if session_state is None:
        session_state = SessionState()

    # Show startup banner
    _show_startup_banner(session_state)

    # Model selection at startup if multiple models available and no model specified
    available_models = get_available_models()
    if not session_state.model and len(available_models) > 1 and not session_state.no_splash:
        console.print("[dim]Multiple models available. Select one to start:[/dim]")
        console.print()
        selected = show_model_selector()
        if selected:
            session_state.model = selected.id
            console.print(f"[dim]Selected model: {selected.id}[/dim]")
        else:
            # Use default if cancelled
            console.print("[dim]Using default model.[/dim]")
        console.print()
    elif not session_state.model and len(available_models) == 1:
        # Auto-select the only available model
        session_state.model = available_models[0].id

    # Create the agent
    # yolo mode: If auto_approve is set initially, skip HITL entirely at agent level
    # Otherwise, HITL is handled at runtime via session_state.auto_approve
    try:
        kai_agent, graph, current_model = _create_kai_agent(
            yolo=False, model=session_state.model
        )  # Always create with HITL enabled
        session_state.model = current_model  # Store the actual model used
        model_display = format_current_model(current_model) or current_model
        console.print(f"[dim]Model: {model_display}[/dim]")
    except Exception as e:
        console.print(f"[red]Error creating agent: {e}[/red]")
        import traceback

        traceback.print_exc()
        return

    # Configure task manager
    task_manager = get_task_manager()
    root_dir = rich_settings.project_root or Path.cwd()
    task_manager.configure(root_dir=root_dir)

    # Create token tracker and image tracker
    token_tracker = TokenTracker()
    image_tracker = ImageTracker()

    # Set context limit based on the selected model
    if session_state.model:
        context_limit = get_context_limit(session_state.model)
        token_tracker.set_context_limit(context_limit)

    # Background task callback for Ctrl+B
    def on_background_task(text: str, is_shell: bool) -> None:
        """Handle Ctrl+B to run task in background."""
        if is_shell:
            task_id = task_manager.run_shell(text)
            console.print(f"[dim]Background shell task started: {task_id}[/dim]")
        else:
            task_id = task_manager.run_agent(text)
            console.print(f"[dim]Background agent task started: {task_id}[/dim]")
        console.print("[dim]Type /tasks to view progress.[/dim]")
        console.print()

    # Create prompt session
    # Assistant ID is used for file path resolution
    assistant_id = "kai"
    prompt_session = create_prompt_session(
        assistant_id,
        session_state,
        image_tracker=image_tracker,
        background_task_callback=on_background_task,
        token_tracker=token_tracker,
    )

    # Handle initial prompt if provided
    if initial_prompt:
        try:
            await execute_task(
                initial_prompt,
                graph,  # Pass the LangGraph graph for streaming
                assistant_id,
                session_state,
                token_tracker=token_tracker,
                backend=kai_agent.backend,
                image_tracker=image_tracker,
            )
        except KeyboardInterrupt:
            pass

    # Main input loop
    while True:
        try:
            # Get user input with prompt-toolkit
            user_input = await asyncio.to_thread(prompt_session.prompt)
            user_input = user_input.strip()

            if not user_input:
                continue

            # Handle bash commands (starting with !)
            if user_input.startswith("!"):
                execute_bash_command(user_input)
                continue

            if user_input.startswith("/"):
                result = handle_command(user_input, kai_agent, token_tracker, session_state)
                if result == "exit":
                    # Clean up background tasks
                    killed = task_manager.kill_all()
                    if killed:
                        console.print(f"[dim]Killed {killed} background task(s).[/dim]")
                    try:
                        kai_agent.save()
                    except Exception:
                        pass
                    console.print("Goodbye!", style=COLORS["dim"])
                    break
                if result == "model_select":
                    # Handle interactive model selection
                    selected = show_model_selector(current_model=session_state.model)
                    if selected and selected.handle != session_state.model:
                        console.print(f"[dim]Switching to model: {selected.id}[/dim]")
                        try:
                            kai_agent, graph, current_model = _create_kai_agent(
                                yolo=False, model=selected.id
                            )
                            session_state.model = current_model
                            # Update context limit for the new model
                            context_limit = get_context_limit(current_model)
                            token_tracker.set_context_limit(context_limit)
                            console.print(f"[green]Model switched to: {format_current_model(current_model)}[/green]")
                        except Exception as e:
                            console.print(f"[red]Failed to switch model: {e}[/red]")
                    continue
                if result is None:
                    continue
                user_input = result

            # Execute the task through the agent
            await execute_task(
                user_input,
                graph,  # Pass the LangGraph graph for streaming
                assistant_id,
                session_state,
                token_tracker=token_tracker,
                backend=kai_agent.backend,
                image_tracker=image_tracker,
            )

        except KeyboardInterrupt:
            # This shouldn't normally happen as prompt-toolkit handles Ctrl+C
            # but if it does, treat it as a request to start fresh
            console.print()
            continue

        except EOFError:
            # User pressed Ctrl+D - exit gracefully
            # Clean up background tasks
            killed = task_manager.kill_all()
            if killed:
                console.print(f"[dim]Killed {killed} background task(s).[/dim]")
            # Save agent state before exiting
            try:
                kai_agent.save()
            except Exception:
                pass
            console.print("\nGoodbye!", style=COLORS["dim"])
            break


def main(args: list[str] | None = None) -> int:
    """Main entry point for the Rich CLI.

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

            console.print(f"kai-code {__version__}")
        except ImportError:
            console.print("kai-code (development)")
        return 0

    # Handle --help-commands
    if parsed.help_commands:
        show_interactive_help()
        return 0

    # Handle --interactive (now just runs the Rich CLI)
    # Note: Textual TUI has been removed, using Rich CLI instead

    # Create session state
    session_state = SessionState(
        auto_approve=parsed.auto_approve,
        no_splash=parsed.no_splash,
        model=parsed.model,
        show_tokens=parsed.show_tokens,
    )

    # Get initial prompt from positional arguments
    initial_prompt = " ".join(parsed.prompt) if parsed.prompt else None

    # Handle Ralph mode - activate loop before running CLI
    if parsed.ralph:
        # Need to create agent first to access ralph_manager
        from kai_code.agent import KaiAgent
        from pathlib import Path

        root_dir = Path.cwd()
        # Get model string
        model_string = _get_model_string(parsed.model)

        # Create a temporary agent just for Ralph setup
        temp_agent = KaiAgent(
            root_dir=root_dir,
            model=model_string,
            yolo=parsed.auto_approve,
        )

        # Start Ralph loop
        temp_agent.ralph_manager.start_loop(
            prompt=initial_prompt or "Continue working on the task",
            completion_promise=parsed.ralph_promise,
            max_iterations=parsed.ralph_max_iterations,
            timeout_seconds=parsed.ralph_timeout,
            token_limit=parsed.ralph_token_limit,
        )

        console.print()
        console.print("⟳ [bold cyan]Ralph autonomous loop activated![/bold cyan]")
        console.print(f"[dim]Prompt: {temp_agent.ralph_manager.get_prompt()}[/dim]")
        if parsed.ralph_promise:
            console.print(f"[dim]Completion promise: {parsed.ralph_promise}[/dim]")
        console.print(f"[dim]Max iterations: {parsed.ralph_max_iterations}[/dim]")
        if parsed.ralph_timeout:
            console.print(f"[dim]Timeout: {parsed.ralph_timeout}s[/dim]")
        console.print(f"[dim]Token limit: {parsed.ralph_token_limit:,}[/dim]")
        console.print()

    # Run the CLI
    try:
        asyncio.run(
            simple_cli(initial_prompt=initial_prompt, session_state=session_state)
        )
        return 0
    except KeyboardInterrupt:
        console.print("\nGoodbye!", style=COLORS["dim"])
        return 0
    except Exception as e:
        console.print(f"[red]Fatal error: {e}[/red]")
        return 1


def cli_main() -> None:
    """CLI entry point that handles exit codes properly."""
    sys.exit(main())


if __name__ == "__main__":
    cli_main()
