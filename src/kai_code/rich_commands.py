"""Command handling for slash commands and bash commands in the Rich CLI.

Adapted from deepagents-cli for kai-code.
"""

import subprocess
from pathlib import Path
from typing import TYPE_CHECKING, Callable

from kai_code.rich_config import console, COLORS, rich_settings
from kai_code.cli_ui import TokenTracker, show_interactive_help
from kai_code.skills import discover_skills_legacy
from kai_code.errors import ActionableError, ErrorType, render_error
from kai_code.error_suggestions import (
    make_unknown_command_error,
    make_missing_argument_error,
    make_invalid_flag_error,
)
from kai_code.settings import export_settings, import_settings

if TYPE_CHECKING:
    from kai_code.model import ModelInfo


def handle_command(
    command_input: str,
    agent,
    token_tracker: TokenTracker | None = None,
) -> str | None:
    """Handle slash commands like /help, /clear, /tokens, /quit.

    Args:
        command_input: The command string starting with /
        agent: The agent instance (for /clear)
        token_tracker: Token tracker for /tokens command

    Returns:
        "exit" if user wants to exit, None if command was handled, or the original
        input if not a valid command
    """
    command = command_input.strip().lower()

    if command in ("/quit", "/exit", "/q"):
        return "exit"

    if command == "/help":
        show_interactive_help()
        return None

    if command == "/clear":
        console.clear()
        if token_tracker:
            token_tracker.reset()
        console.print("Conversation cleared.", style=COLORS["dim"])
        console.print()
        return None

    if command == "/tokens":
        if token_tracker:
            token_tracker.display_session()
        else:
            console.print("Token tracking not available.", style=COLORS["dim"])
        return None

    if command == "/skills":
        _show_skills()
        return None

    if command == "/brainstorm" or command.startswith("/brainstorm "):
        return _handle_brainstorm(command_input)

    if command == "/models" or command.startswith("/models "):
        # Check for refresh subcommand
        parts = command_input.strip().split()
        if len(parts) > 1 and parts[1].lower() == "refresh":
            from kai_code.model import refresh_models
            console.print("[dim]Refreshing models from APIs...[/dim]")
            refresh_models()
        # Interactive model selector - return special value to signal main loop
        return "model_select"

    if command == "/model":
        # Interactive model selector - return special value to signal main loop
        return "model_select"

    if command in ("/tasks", "/task"):
        _show_tasks()
        return None

    # Ralph commands
    if command.startswith("/ralph-loop"):
        return _handle_ralph_loop(command_input, agent)

    if command in ("/cancel-ralph", "/ralph-cancel", "/stop-ralph"):
        return _handle_cancel_ralph(agent)

    if command in ("/ralph-status", "/ralph"):
        _show_ralph_status(agent)
        return None

    # Settings export command
    if command == "/export-settings" or command.startswith("/export-settings "):
        _handle_export_settings(command_input)
        return None

    # Settings import command
    if command == "/import-settings" or command.startswith("/import-settings "):
        _handle_import_settings(command_input)
        return None

    # Unknown command - show actionable error with suggestions
    available_commands = [
        "/help", "/clear", "/tokens", "/quit", "/exit", "/q",
        "/skills", "/brainstorm", "/models", "/model", "/tasks", "/task",
        "/ralph-loop", "/cancel-ralph", "/ralph-cancel", "/stop-ralph",
        "/ralph-status", "/ralph", "/export-settings", "/import-settings",
    ]
    error = make_unknown_command_error(command_input, available_commands)
    error.severity = "warning"  # Use warning since it's not fatal
    render_error(error, console)
    return None


def execute_bash_command(command_input: str) -> None:
    """Execute a bash command (input starts with !).

    Args:
        command_input: The command string starting with !
    """
    # Strip the leading ! and any whitespace
    bash_command = command_input[1:].strip()

    if not bash_command:
        error = make_missing_argument_error(
            command="!",
            missing_arg="command",
            expected_type="shell command",
            usage_example="!ls -la",
        )
        error.severity = "warning"
        render_error(error, console)
        return

    console.print()
    console.print(f"[dim]$ {bash_command}[/dim]")
    console.print()

    try:
        result = subprocess.run(
            bash_command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout
        )

        if result.stdout:
            # Limit output to prevent overwhelming the terminal
            output = result.stdout
            if len(output) > 10000:
                output = output[:10000] + "\n... (output truncated)"
            console.print(output, markup=False)

        if result.stderr:
            console.print(result.stderr, style="red", markup=False)

        if result.returncode != 0:
            console.print(
                f"[yellow]Command exited with code {result.returncode}[/yellow]"
            )

    except subprocess.TimeoutExpired:
        error = ActionableError(
            error_type=ErrorType.TIMEOUT_ERROR,
            message=f"Command timed out after 5 minutes: '{bash_command}'",
            suggestions=[
                "The command took too long to complete",
                "Consider running long commands in the background with '&'",
                "Break the command into smaller parts",
            ],
            recovery_commands=[
                f"# Run in background: !{bash_command} &",
                "# Or increase timeout by running separately",
            ],
            context={"command": bash_command, "timeout": "300s"},
        )
        render_error(error, console)
    except Exception as e:
        error = ActionableError(
            error_type=ErrorType.COMMAND_EXECUTION_ERROR,
            message=f"Error executing command: {e}",
            suggestions=[
                "Check if the command is valid",
                "Verify required tools/binaries are installed",
                "Check file paths and permissions",
            ],
            recovery_commands=[
                f"which {bash_command.split()[0]}" if bash_command.split() else "# Check command syntax",
            ],
            context={"command": bash_command, "error": str(e)},
        )
        render_error(error, console)

    console.print()


def _show_skills() -> None:
    """Display available skills."""
    root_dir = rich_settings.project_root or Path.cwd()

    # Discover skills from project .skills directory
    project_skills = discover_skills_legacy(root_dir, ".skills")

    # Discover skills from user ~/.kai/skills directory
    user_skills_dir = rich_settings.user_kai_dir / "skills"
    user_skills = []
    if user_skills_dir.exists():
        # Use Path.cwd() as root since user skills are global
        user_skills = discover_skills_legacy(user_skills_dir.parent, "skills")

    console.print()
    console.print("[bold]Available Skills[/bold]")
    console.print()

    if not project_skills and not user_skills:
        console.print("No skills found.", style=COLORS["dim"])
        console.print()
        console.print(
            f"Add skills to {root_dir / '.skills'} or {user_skills_dir}",
            style=COLORS["dim"],
        )
    else:
        if project_skills:
            console.print("[bold]Project Skills:[/bold]")
            for skill in project_skills:
                console.print(f"  • {skill.skill_id}", style=COLORS["primary"])
            console.print()

        if user_skills:
            console.print("[bold]User Skills:[/bold]")
            for skill in user_skills:
                console.print(f"  • {skill.skill_id}", style=COLORS["primary"])
            console.print()

    console.print(
        "Use a skill: Just describe what you want and the agent will use relevant skills.",
        style=COLORS["dim"],
    )
    console.print()


def _show_tasks() -> None:
    """Display the background tasks panel."""
    from kai_code.tasks import show_tasks_panel
    show_tasks_panel(interactive=True)


def _handle_brainstorm(command_input: str) -> str | None:
    parts = command_input.strip().split(maxsplit=1)
    topic = parts[1] if len(parts) > 1 else None

    skill_path = Path(__file__).parent / "skills" / "brainstorming" / "SKILL.md"

    if not skill_path.exists():
        console.print("[red]Brainstorming skill not found.[/red]")
        return None

    skill_content = skill_path.read_text(encoding="utf-8")

    console.print()
    console.print("[bold cyan]Starting brainstorm session...[/bold cyan]")
    console.print()

    if topic:
        console.print(f"[dim]Topic: {topic}[/dim]")
        console.print()
        return f"""I want to brainstorm and design: {topic}

Please follow the brainstorming process below to help me refine this idea into a complete design.

---

{skill_content}

---

Start by exploring the current project context, then ask me your first question about this idea."""

    return f"""I want to brainstorm a new idea.

Please follow the brainstorming process below to help me refine my idea into a complete design.

---

{skill_content}

---

Start by asking me what I'd like to brainstorm today."""


def _handle_ralph_loop(command_input: str, agent) -> str | None:
    """Handle /ralph-loop command.

    Args:
        command_input: The full command string
        agent: The agent instance

    Returns:
        The prompt to execute, or None if error
    """
    import shlex

    parts = shlex.split(command_input.strip())

    # Define valid flags for error suggestions
    valid_ralph_flags = [
        "--promise", "--completion-promise",
        "--max-iterations", "--timeout", "--token-limit",
    ]

    if len(parts) < 2:
        error = make_missing_argument_error(
            command="/ralph-loop",
            missing_arg="prompt",
            expected_type="text describing what the agent should accomplish",
            usage_example='/ralph-loop "implement the login feature" --max-iterations 10',
        )
        error.severity = "warning"
        render_error(error, console)
        return None

    # Parse command - prompt is everything until first flag
    prompt = None
    completion_promise = None
    max_iterations = 50
    timeout_seconds = None
    token_limit = 500_000

    i = 1  # Skip /ralph-loop
    # Collect prompt until we hit a flag
    prompt_parts = []
    while i < len(parts) and not parts[i].startswith("--"):
        prompt_parts.append(parts[i])
        i += 1

    if not prompt_parts:
        error = make_missing_argument_error(
            command="/ralph-loop",
            missing_arg="prompt",
            expected_type="text describing what the agent should accomplish",
            usage_example='/ralph-loop "implement the login feature" --max-iterations 10',
        )
        error.severity = "warning"
        render_error(error, console)
        return None

    prompt = " ".join(prompt_parts)

    # Parse flags
    while i < len(parts):
        flag = parts[i]
        if flag in ("--promise", "--completion-promise"):
            if i + 1 < len(parts):
                completion_promise = parts[i + 1]
                i += 2
            else:
                error = make_missing_argument_error(
                    command="/ralph-loop",
                    missing_arg=f"value for {flag}",
                    expected_type="text describing the completion criteria",
                    usage_example=f'/ralph-loop "my task" {flag} "all tests pass"',
                )
                error.severity = "warning"
                render_error(error, console)
                return None
        elif flag == "--max-iterations":
            if i + 1 < len(parts):
                try:
                    max_iterations = int(parts[i + 1])
                    i += 2
                except ValueError:
                    error = ActionableError(
                        error_type=ErrorType.VALIDATION_ERROR,
                        message=f"Invalid value for --max-iterations: '{parts[i + 1]}' is not a number",
                        suggestions=[
                            "--max-iterations requires an integer value",
                            "This sets the maximum number of agent iterations",
                        ],
                        recovery_commands=[
                            '/ralph-loop "my task" --max-iterations 50',
                        ],
                        context={"flag": "--max-iterations", "value": parts[i + 1]},
                        severity="warning",
                    )
                    render_error(error, console)
                    return None
            else:
                error = make_missing_argument_error(
                    command="/ralph-loop",
                    missing_arg="value for --max-iterations",
                    expected_type="integer (number of iterations)",
                    usage_example='/ralph-loop "my task" --max-iterations 50',
                )
                error.severity = "warning"
                render_error(error, console)
                return None
        elif flag == "--timeout":
            if i + 1 < len(parts):
                try:
                    timeout_seconds = int(parts[i + 1])
                    i += 2
                except ValueError:
                    error = ActionableError(
                        error_type=ErrorType.VALIDATION_ERROR,
                        message=f"Invalid value for --timeout: '{parts[i + 1]}' is not a number",
                        suggestions=[
                            "--timeout requires an integer value (seconds)",
                            "This sets the maximum time before the loop stops",
                        ],
                        recovery_commands=[
                            '/ralph-loop "my task" --timeout 3600',
                        ],
                        context={"flag": "--timeout", "value": parts[i + 1]},
                        severity="warning",
                    )
                    render_error(error, console)
                    return None
            else:
                error = make_missing_argument_error(
                    command="/ralph-loop",
                    missing_arg="value for --timeout",
                    expected_type="integer (seconds)",
                    usage_example='/ralph-loop "my task" --timeout 3600',
                )
                error.severity = "warning"
                render_error(error, console)
                return None
        elif flag == "--token-limit":
            if i + 1 < len(parts):
                try:
                    token_limit = int(parts[i + 1])
                    i += 2
                except ValueError:
                    error = ActionableError(
                        error_type=ErrorType.VALIDATION_ERROR,
                        message=f"Invalid value for --token-limit: '{parts[i + 1]}' is not a number",
                        suggestions=[
                            "--token-limit requires an integer value",
                            "This sets the maximum tokens before the loop stops",
                        ],
                        recovery_commands=[
                            '/ralph-loop "my task" --token-limit 500000',
                        ],
                        context={"flag": "--token-limit", "value": parts[i + 1]},
                        severity="warning",
                    )
                    render_error(error, console)
                    return None
            else:
                error = make_missing_argument_error(
                    command="/ralph-loop",
                    missing_arg="value for --token-limit",
                    expected_type="integer (number of tokens)",
                    usage_example='/ralph-loop "my task" --token-limit 500000',
                )
                error.severity = "warning"
                render_error(error, console)
                return None
        else:
            # Unknown flag - use make_invalid_flag_error with suggestions
            error = make_invalid_flag_error(
                flag=flag,
                valid_flags=valid_ralph_flags,
                command="/ralph-loop",
            )
            error.severity = "warning"
            render_error(error, console)
            i += 1

    # Start Ralph loop
    agent.ralph_manager.start_loop(
        prompt=prompt,
        completion_promise=completion_promise,
        max_iterations=max_iterations,
        timeout_seconds=timeout_seconds,
        token_limit=token_limit,
    )

    console.print()
    console.print("⟳ [bold cyan]Ralph autonomous loop started![/bold cyan]")
    console.print(f"[dim]Prompt: {prompt}[/dim]")
    if completion_promise:
        console.print(f"[dim]Completion promise: {completion_promise}[/dim]")
    console.print(f"[dim]Max iterations: {max_iterations}[/dim]")
    if timeout_seconds:
        console.print(f"[dim]Timeout: {timeout_seconds}s[/dim]")
    console.print(f"[dim]Token limit: {token_limit:,}[/dim]")
    console.print()

    # Return the prompt to execute
    return prompt


def _handle_cancel_ralph(agent) -> None:
    """Handle /cancel-ralph command.

    Args:
        agent: The agent instance

    Returns:
        None
    """
    if not agent.ralph_manager.is_active():
        console.print("[dim]No active Ralph loop.[/dim]")
        return None

    agent.ralph_manager.cancel_loop()
    console.print("⚠ [yellow]Ralph loop canceled.[/yellow]")
    return None


def _show_ralph_status(agent) -> None:
    """Display Ralph loop status.

    Args:
        agent: The agent instance
    """
    if not agent.ralph_manager.is_active():
        console.print()
        console.print("[bold]Ralph Loop Status[/bold]")
        console.print()
        console.print("Status: [dim]Inactive[/dim]")
        console.print()
        console.print("[dim]Use /ralph-loop to start an autonomous loop.[/dim]")
        console.print()
        return

    state = agent.ralph_manager.get_state()
    if not state:
        console.print("[yellow]Error: Could not get Ralph loop state[/yellow]")
        return

    console.print()
    console.print("[bold]Ralph Loop Status[/bold]")
    console.print()
    console.print("Status: [green]Active[/green] ⟳")
    console.print()
    console.print(f"Prompt: [dim]{state.prompt}[/dim]")

    if state.completion_promise:
        console.print(f"Completion promise: [dim]{state.completion_promise}[/dim]")

    max_iter = state.max_iterations or "∞"
    console.print(f"Iteration: [cyan]{state.current_iteration}/{max_iter}[/cyan]")

    if state.token_limit:
        console.print(
            f"Tokens: [cyan]{state.total_tokens:,}/{state.token_limit:,}[/cyan]"
        )
    else:
        console.print(f"Tokens: [cyan]{state.total_tokens:,}[/cyan]")

    if state.timeout_seconds:
        import time

        elapsed = int(time.time() - state.started_at)
        remaining = state.timeout_seconds - elapsed
        console.print(
            f"Timeout: [dim]{elapsed}s / {state.timeout_seconds}s ({remaining}s remaining)[/dim]"
        )

    console.print()
    console.print("[dim]Use /cancel-ralph to stop the loop.[/dim]")
    console.print()


def _handle_export_settings(command_input: str) -> None:
    """Handle /export-settings command."""
    parts = command_input.strip().split(maxsplit=1)
    filename = parts[1] if len(parts) > 1 else "kai-settings.json"

    try:
        result = export_settings(filename)
        console.print(f"[green]{result}[/green]")
    except Exception as e:
        error = ActionableError(
            error_type=ErrorType.FILE_ERROR,
            message=f"Failed to export settings: {e}",
            suggestions=[
                "Check if you have write permissions to the target directory",
                "Try using a different filename or path",
            ],
            recovery_commands=[
                f"# Try exporting to home directory: /export-settings ~/kai-settings.json",
            ],
            context={"filename": filename},
        )
        render_error(error, console)


def _handle_import_settings(command_input: str) -> None:
    """Handle /import-settings command."""
    parts = command_input.strip().split(maxsplit=1)

    if len(parts) < 2:
        error = make_missing_argument_error(
            command="/import-settings",
            missing_arg="filename",
            expected_type="path to settings file",
            usage_example="/import-settings kai-settings.json",
        )
        error.severity = "warning"
        render_error(error, console)
        return

    filename = parts[1]

    try:
        result = import_settings(filename)
        console.print(f"[green]{result}[/green]")
    except FileNotFoundError:
        error = ActionableError(
            error_type=ErrorType.FILE_NOT_FOUND,
            message=f"Settings file not found: {filename}",
            suggestions=[
                "Check if the file path is correct",
                "Use /export-settings to create a settings file first",
            ],
            recovery_commands=[
                "# List files in current directory: !ls -la",
                f"# Check if file exists: !ls -la {filename}",
            ],
            context={"filename": filename},
        )
        render_error(error, console)
    except Exception as e:
        error = ActionableError(
            error_type=ErrorType.CONFIG_ERROR,
            message=f"Failed to import settings: {e}",
            suggestions=[
                "Check if the file contains valid JSON",
                "Ensure the settings format is correct",
            ],
            context={"filename": filename, "error": str(e)},
        )
        render_error(error, console)
