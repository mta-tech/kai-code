"""Slash command handlers for kai-dbt CLI."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import TYPE_CHECKING, Any

from kai_code.errors import ActionableError, ErrorType
from kai_code.error_suggestions import (
    make_dbt_command_error,
    make_dbt_connection_error,
    make_dbt_model_not_found_error,
    make_missing_argument_error,
    make_unknown_command_error,
    suggest_values,
)

from .banner import format_schema_summary

if TYPE_CHECKING:
    from .agent import DbtAgent


def _format_error_for_command(error: ActionableError) -> str:
    """Format an ActionableError as a readable string for command output.

    Since command handlers return strings, we format the error
    as plain text that users can read and act upon.

    Args:
        error: The ActionableError to format.

    Returns:
        A formatted string representation of the error.
    """
    lines = [f"Error ({error.error_type.value}): {error.message}"]

    if error.suggestions:
        lines.append("\nSuggestions:")
        for suggestion in error.suggestions:
            lines.append(f"  • {suggestion}")

    if error.related_items:
        lines.append(f"\nDid you mean: {', '.join(error.related_items)}")

    if error.recovery_commands:
        lines.append("\nTry these commands:")
        for cmd in error.recovery_commands:
            if cmd.startswith("#"):
                lines.append(f"  {cmd}")
            else:
                lines.append(f"  $ {cmd}")

    return "\n".join(lines)


def parse_dbt_command(command: str) -> tuple[str, dict[str, Any]]:
    """Parse a dbt slash command into command name and arguments.

    Args:
        command: Full command string (e.g., "/dbt run stg_orders").

    Returns:
        Tuple of (command_name, arguments_dict).
    """
    parts = command.strip().split()

    if not parts:
        return "", {}

    # Handle /dbt subcommands
    if parts[0] == "/dbt" and len(parts) >= 2:
        subcommand = parts[1]
        args: dict[str, Any] = {}

        if subcommand == "run" and len(parts) > 2:
            args["select"] = parts[2]
        elif subcommand == "test" and len(parts) > 2:
            args["select"] = parts[2]
        elif subcommand == "compile" and len(parts) > 2:
            args["model"] = parts[2]
        elif subcommand == "show" and len(parts) > 2:
            args["model"] = parts[2]

        return subcommand, args

    # Handle direct commands
    if parts[0] == "/schema":
        return "schema", {}

    if parts[0] == "/model" and len(parts) > 1:
        return "model", {"name": parts[1]}

    if parts[0] == "/model":
        return "model", {}

    if parts[0] == "/brainstorm":
        return "brainstorm", {}

    if parts[0] == "/ralph-patterns":
        return "ralph-patterns", {}

    if parts[0] == "/ralph-pattern" and len(parts) > 1:
        return "ralph-pattern", {"name": parts[1]}

    if parts[0] == "/ralph-pattern":
        return "ralph-pattern", {}

    if parts[0] == "/help":
        return "help", {}

    if parts[0] == "/exit" or parts[0] == "/quit":
        return "exit", {}

    return parts[0].lstrip("/"), {}


class DbtCommandHandler:
    """Handler for dbt-specific slash commands."""

    def __init__(self, agent: "DbtAgent"):
        """Initialize command handler.

        Args:
            agent: DbtAgent instance.
        """
        self.agent = agent

    def handle(self, command: str) -> str | None:
        """Handle a slash command.

        Args:
            command: Command string.

        Returns:
            Command output string, or None if command not recognized.
        """
        cmd, args = parse_dbt_command(command)

        handlers = {
            "schema": self._handle_schema,
            "model": self._handle_model,
            "run": self._handle_dbt_run,
            "test": self._handle_dbt_test,
            "compile": self._handle_dbt_compile,
            "list": self._handle_dbt_list,
            "show": self._handle_dbt_show,
            "brainstorm": self._handle_brainstorm,
            "help": self._handle_help,
            "ralph-pattern": self._handle_ralph_pattern,
            "ralph-patterns": self._handle_list_ralph_patterns,
        }

        handler = handlers.get(cmd)
        if handler:
            return handler(args)

        return None

    def _handle_help(self, args: dict) -> str:
        """Handle /help command."""
        return """
dbt Slash Commands:

  /schema              Show database schema summary
  /model <name>        Show model details and columns
  /dbt run [model]     Run dbt models
  /dbt test [model]    Run dbt tests
  /dbt compile [model] Compile dbt models
  /dbt list            List dbt resources
  /dbt show <model>    Preview model output
  /brainstorm [topic]  Start a design brainstorm session
  /ralph-patterns      List available Ralph autonomous patterns
  /ralph-pattern <name> Start a Ralph pattern (e.g., test-until-pass)
  /help                Show this help
  /exit                Exit kai-dbt
"""

    def _handle_schema(self, args: dict) -> str:
        """Handle /schema command."""
        if not self.agent.adapter:
            error = make_dbt_connection_error(
                error_details="No database adapter configured for the dbt agent"
            )
            error = ActionableError(
                error_type=ErrorType.DBT_CONNECTION_ERROR,
                message="No database connected",
                suggestions=[
                    "Use the --db flag to specify a database connection",
                    "Check your dbt profile configuration in ~/.dbt/profiles.yml",
                    "Ensure your database is running and accessible",
                ],
                recovery_commands=[
                    "kai-dbt --db path/to/database.duckdb",
                    "dbt debug",
                    "cat ~/.dbt/profiles.yml",
                ],
                context={"project_dir": str(self.agent.dbt_project_dir)},
                severity="warning",
            )
            return _format_error_for_command(error)

        try:
            tables = self.agent.adapter.get_tables()
            table_data = [
                {
                    "name": t.name,
                    "column_count": t.column_count,
                    "row_count": t.row_count,
                }
                for t in tables
            ]
            return format_schema_summary(table_data)
        except Exception as e:
            error = make_dbt_command_error(
                command="/schema",
                error_output=str(e),
                model_name=None,
            )
            return _format_error_for_command(error)

    def _handle_model(self, args: dict) -> str:
        """Handle /model <name> command."""
        model_name = args.get("name")
        if not model_name:
            error = make_missing_argument_error(
                command="/model",
                missing_arg="model_name",
                expected_type="dbt model name (e.g., stg_orders, dim_customers)",
                usage_example="/model stg_orders",
            )
            return _format_error_for_command(error)

        if not self.agent.adapter:
            error = ActionableError(
                error_type=ErrorType.DBT_CONNECTION_ERROR,
                message="No database connected",
                suggestions=[
                    "Use the --db flag to specify a database connection",
                    "Check your dbt profile configuration",
                    "Ensure your database is running and accessible",
                ],
                recovery_commands=[
                    "kai-dbt --db path/to/database.duckdb",
                    "dbt debug",
                ],
                context={
                    "project_dir": str(self.agent.dbt_project_dir),
                    "requested_model": model_name,
                },
                severity="warning",
            )
            return _format_error_for_command(error)

        try:
            columns = self.agent.adapter.get_columns(model_name)
            if not columns:
                # Try to get available models for suggestions
                available_models: list[str] = []
                try:
                    tables = self.agent.adapter.get_tables()
                    available_models = [t.name for t in tables]
                except Exception:
                    pass

                error = make_dbt_model_not_found_error(
                    model_name=model_name,
                    available_models=available_models,
                    project_dir=str(self.agent.dbt_project_dir),
                )
                return _format_error_for_command(error)

            lines = [f"Model: {model_name}", ""]
            lines.append("Columns:")
            for col in columns:
                pk = " (PK)" if col.is_primary_key else ""
                nullable = " NULL" if col.is_nullable else " NOT NULL"
                lines.append(f"  - {col.name}: {col.data_type}{pk}{nullable}")

            return "\n".join(lines)
        except Exception as e:
            error = make_dbt_command_error(
                command=f"/model {model_name}",
                error_output=str(e),
                model_name=model_name,
            )
            return _format_error_for_command(error)

    def _handle_dbt_run(self, args: dict) -> str:
        """Handle /dbt run command."""
        return self._run_dbt_command(["run"], args.get("select"))

    def _handle_dbt_test(self, args: dict) -> str:
        """Handle /dbt test command."""
        return self._run_dbt_command(["test"], args.get("select"))

    def _handle_dbt_compile(self, args: dict) -> str:
        """Handle /dbt compile command."""
        return self._run_dbt_command(["compile"], args.get("model"))

    def _handle_dbt_list(self, args: dict) -> str:
        """Handle /dbt list command."""
        return self._run_dbt_command(["list"])

    def _handle_dbt_show(self, args: dict) -> str:
        """Handle /dbt show command."""
        model = args.get("model")
        if not model:
            error = make_missing_argument_error(
                command="/dbt show",
                missing_arg="model_name",
                expected_type="dbt model name to preview (e.g., stg_orders)",
                usage_example="/dbt show stg_orders",
            )
            return _format_error_for_command(error)
        return self._run_dbt_command(["show", "--select", model], model_name=model)

    def _handle_brainstorm(self, args: dict) -> str:
        """Handle /brainstorm command.

        This command initiates an interactive design brainstorm session for dbt models,
        helping users think through data modeling decisions, relationships, and best practices.
        """
        return """
🧠 Design Brainstorm Mode

I'm ready to help you brainstorm and design your dbt data models!

Tell me what you'd like to work on. For example:

• "I need to track customer orders across multiple channels"
• "How should I model slowly changing dimensions?"
• "Help me design a staging layer for Stripe data"
• "What's the best way to handle currency conversions?"
• "I need to create a customer 360 view"

I'll help you think through:
  ✓ Entity relationships and foreign keys
  ✓ Granularity and primary keys
  ✓ Staging vs intermediate vs marts placement
  ✓ Naming conventions and dbt best practices
  ✓ Performance considerations
  ✓ Testing strategies

What would you like to brainstorm about?
"""

    def _run_dbt_command(
        self,
        command: list[str],
        select: str | None = None,
        model_name: str | None = None,
    ) -> str:
        """Run a dbt CLI command.

        Args:
            command: dbt command arguments.
            select: Optional model selection.
            model_name: Optional explicit model name for error context.

        Returns:
            Command output.
        """
        full_command = ["dbt"] + command

        if select:
            full_command.extend(["--select", select])

        full_command.extend(
            [
                "--project-dir",
                str(self.agent.dbt_project_dir),
            ]
        )

        if self.agent.dbt_profiles_dir:
            full_command.extend(
                [
                    "--profiles-dir",
                    str(self.agent.dbt_profiles_dir),
                ]
            )

        # Determine model name for error context
        effective_model = model_name or select
        command_str = " ".join(["dbt"] + command)

        try:
            result = subprocess.run(
                full_command,
                capture_output=True,
                text=True,
                timeout=300,
                cwd=str(self.agent.dbt_project_dir),
            )

            if result.returncode == 0:
                return result.stdout or "Command completed successfully."
            else:
                # Use make_dbt_command_error for non-zero exit codes
                error_output = result.stderr or result.stdout
                error = make_dbt_command_error(
                    command=command_str,
                    error_output=error_output,
                    exit_code=result.returncode,
                    model_name=effective_model,
                )
                return _format_error_for_command(error)

        except subprocess.TimeoutExpired:
            error = ActionableError(
                error_type=ErrorType.TIMEOUT_ERROR,
                message=f"dbt command '{command_str}' timed out after 5 minutes",
                suggestions=[
                    "The command took too long to complete",
                    "Try running with a smaller selection of models",
                    "Use --threads 1 to reduce parallelism",
                    "Check if the database is responding slowly",
                ],
                recovery_commands=[
                    f"dbt {command[0]} --select <single_model> --threads 1",
                    "dbt debug",
                    "# Run in smaller batches",
                ],
                context={
                    "command": command_str,
                    "timeout_seconds": "300",
                    "model": effective_model or "(all models)",
                },
                severity="error",
            )
            return _format_error_for_command(error)
        except FileNotFoundError:
            error = ActionableError(
                error_type=ErrorType.COMMAND_NOT_FOUND,
                message="dbt command not found",
                suggestions=[
                    "dbt is not installed or not in your PATH",
                    "Install dbt using pip or your package manager",
                    "Ensure dbt is in your virtual environment if using one",
                ],
                recovery_commands=[
                    "pip install dbt-core",
                    "pip install dbt-duckdb  # for DuckDB adapter",
                    "pip install dbt-postgres  # for PostgreSQL adapter",
                    "which dbt  # verify installation",
                    "dbt --version",
                ],
                context={"command": command_str},
                severity="error",
            )
            return _format_error_for_command(error)
        except Exception as e:
            error = make_dbt_command_error(
                command=command_str,
                error_output=str(e),
                model_name=effective_model,
            )
            return _format_error_for_command(error)

    def _handle_ralph_pattern(self, args: dict) -> str:
        """Handle /ralph-pattern <name> command."""
        from .ralph_patterns import start_dbt_ralph_pattern, DBT_RALPH_PATTERNS

        pattern_name = args.get("name")
        if not pattern_name:
            # Get available patterns for suggestions
            available_patterns = list(DBT_RALPH_PATTERNS.keys()) if DBT_RALPH_PATTERNS else []
            error = make_missing_argument_error(
                command="/ralph-pattern",
                missing_arg="pattern_name",
                expected_type="Ralph pattern name (e.g., test-until-pass, fix-and-run)",
                usage_example="/ralph-pattern test-until-pass --max-iterations 5",
            )
            # Enhance with available patterns if any
            if available_patterns:
                error.suggestions.append(
                    f"Available patterns: {', '.join(available_patterns)}"
                )
            return _format_error_for_command(error)

        try:
            result = start_dbt_ralph_pattern(self.agent, pattern_name)
            return result
        except ValueError as e:
            # ValueError typically means invalid pattern name or configuration
            available_patterns = list(DBT_RALPH_PATTERNS.keys()) if DBT_RALPH_PATTERNS else []
            similar = suggest_values(pattern_name, available_patterns, n=3, cutoff=0.5)

            error = ActionableError(
                error_type=ErrorType.VALIDATION_ERROR,
                message=str(e),
                suggestions=[
                    "Check if the pattern name is spelled correctly",
                    "Use /ralph-patterns to see available patterns",
                ],
                recovery_commands=[
                    "/ralph-patterns",
                ],
                related_items=similar,
                context={
                    "pattern_name": pattern_name,
                    "available_count": str(len(available_patterns)),
                },
                severity="warning",
            )
            if similar:
                error.suggestions.insert(0, f"Did you mean '{similar[0]}'?")
            return _format_error_for_command(error)
        except Exception as e:
            error = ActionableError(
                error_type=ErrorType.COMMAND_EXECUTION_ERROR,
                message=f"Error starting Ralph pattern '{pattern_name}': {e}",
                suggestions=[
                    "Check if the dbt project is configured correctly",
                    "Verify the database connection is working",
                    "Ensure required models and tests exist",
                ],
                recovery_commands=[
                    "/ralph-patterns",
                    "dbt debug",
                    "dbt list",
                ],
                context={
                    "pattern_name": pattern_name,
                    "error_details": str(e)[:200],
                },
                severity="error",
            )
            return _format_error_for_command(error)

    def _handle_list_ralph_patterns(self, args: dict) -> str:
        """Handle /ralph-patterns command."""
        from .ralph_patterns import list_dbt_ralph_patterns

        try:
            return list_dbt_ralph_patterns()
        except Exception as e:
            error = ActionableError(
                error_type=ErrorType.COMMAND_EXECUTION_ERROR,
                message=f"Error listing Ralph patterns: {e}",
                suggestions=[
                    "There may be an issue with the Ralph patterns configuration",
                    "Try restarting the kai-dbt session",
                ],
                recovery_commands=[
                    "/help",
                ],
                context={"error_details": str(e)[:200]},
                severity="error",
            )
            return _format_error_for_command(error)
