"""Command handling for slash commands and bash commands in the Rich CLI.

Adapted from deepagents-cli for kai-code.
"""

import subprocess
from pathlib import Path
from typing import TYPE_CHECKING, Callable

from kai_code.rich_config import console, COLORS, rich_settings
from kai_code.cli_ui import TokenTracker, show_interactive_help
from kai_code.skills import discover_skills_legacy

if TYPE_CHECKING:
    from kai_code.model import ModelInfo
    from kai_code.rich_config import SessionState


def handle_command(
    command_input: str,
    agent,
    token_tracker: TokenTracker | None = None,
    session_state: "SessionState | None" = None,
) -> str | None:
    """Handle slash commands like /help, /clear, /tokens, /quit.

    Args:
        command_input: The command string starting with /
        agent: The agent instance (for /clear)
        token_tracker: Token tracker for /tokens command
        session_state: Session state for toggling token display

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

    if command == "/tokens" or command.startswith("/tokens "):
        return _handle_tokens_command(command_input, token_tracker, session_state)

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

    # Unknown command - let it pass through as regular input
    console.print(
        f"[yellow]Unknown command: {command_input}[/yellow]",
        style=COLORS["dim"],
    )
    console.print("Type /help for available commands.", style=COLORS["dim"])
    return None


def execute_bash_command(command_input: str) -> None:
    """Execute a bash command (input starts with !).

    Args:
        command_input: The command string starting with !
    """
    # Strip the leading ! and any whitespace
    bash_command = command_input[1:].strip()

    if not bash_command:
        console.print("[yellow]No command provided after ![/yellow]")
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
        console.print("[red]Command timed out after 5 minutes[/red]")
    except Exception as e:
        console.print(f"[red]Error executing command: {e}[/red]")

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


def _handle_tokens_command(
    command_input: str,
    token_tracker: TokenTracker | None,
    session_state: "SessionState | None",
) -> None:
    """Handle /tokens command with optional subcommands.

    Subcommands:
        /tokens - Display current token usage and indicator status
        /tokens show - Enable token indicator display
        /tokens hide - Disable token indicator display

    Args:
        command_input: The full command string
        token_tracker: Token tracker for displaying usage
        session_state: Session state for toggling show_tokens setting
    """
    parts = command_input.strip().split()
    subcommand = parts[1].lower() if len(parts) > 1 else None

    if subcommand == "show":
        if session_state:
            session_state.show_tokens = True
            console.print("Token indicator enabled.", style=COLORS["primary"])
        else:
            console.print("Session state not available.", style=COLORS["dim"])
        return None

    if subcommand == "hide":
        if session_state:
            session_state.show_tokens = False
            console.print("Token indicator hidden.", style=COLORS["dim"])
        else:
            console.print("Session state not available.", style=COLORS["dim"])
        return None

    if subcommand is not None:
        # Unknown subcommand
        console.print(f"[yellow]Unknown subcommand: {subcommand}[/yellow]")
        console.print("Usage: /tokens [show|hide]", style=COLORS["dim"])
        return None

    # No subcommand - display token usage and current setting
    console.print()
    if token_tracker:
        token_tracker.display_session()

        # Show current indicator status
        if session_state:
            status = "enabled" if session_state.show_tokens else "disabled"
            status_style = COLORS["primary"] if session_state.show_tokens else COLORS["dim"]
            console.print(f"Token indicator: [{status_style}]{status}[/{status_style}]")
            console.print()
            console.print("Use /tokens show or /tokens hide to toggle.", style=COLORS["dim"])
    else:
        console.print("Token tracking not available.", style=COLORS["dim"])

    console.print()
    return None


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

    if len(parts) < 2:
        console.print(
            "[yellow]Usage: /ralph-loop <prompt> [--promise <text>] [--max-iterations <n>] [--timeout <s>] [--token-limit <n>][/yellow]"
        )
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
        console.print("[yellow]Error: No prompt provided[/yellow]")
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
                console.print(f"[yellow]Error: {flag} requires a value[/yellow]")
                return None
        elif flag == "--max-iterations":
            if i + 1 < len(parts):
                try:
                    max_iterations = int(parts[i + 1])
                    i += 2
                except ValueError:
                    console.print("[yellow]Error: --max-iterations must be a number[/yellow]")
                    return None
            else:
                console.print("[yellow]Error: --max-iterations requires a value[/yellow]")
                return None
        elif flag == "--timeout":
            if i + 1 < len(parts):
                try:
                    timeout_seconds = int(parts[i + 1])
                    i += 2
                except ValueError:
                    console.print("[yellow]Error: --timeout must be a number[/yellow]")
                    return None
            else:
                console.print("[yellow]Error: --timeout requires a value[/yellow]")
                return None
        elif flag == "--token-limit":
            if i + 1 < len(parts):
                try:
                    token_limit = int(parts[i + 1])
                    i += 2
                except ValueError:
                    console.print("[yellow]Error: --token-limit must be a number[/yellow]")
                    return None
            else:
                console.print("[yellow]Error: --token-limit requires a value[/yellow]")
                return None
        else:
            console.print(f"[yellow]Unknown flag: {flag}[/yellow]")
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
