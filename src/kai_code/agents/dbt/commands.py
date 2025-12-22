"""Slash command handlers for kai-dbt CLI."""
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .banner import format_schema_summary

if TYPE_CHECKING:
    from .agent import DbtAgent


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
            "help": self._handle_help,
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
  /help                Show this help
  /exit                Exit kai-dbt
"""

    def _handle_schema(self, args: dict) -> str:
        """Handle /schema command."""
        if not self.agent.adapter:
            return "No database connected. Use --db to connect."

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
            return f"Error fetching schema: {e}"

    def _handle_model(self, args: dict) -> str:
        """Handle /model <name> command."""
        model_name = args.get("name")
        if not model_name:
            return "Usage: /model <model_name>"

        if not self.agent.adapter:
            return "No database connected."

        try:
            columns = self.agent.adapter.get_columns(model_name)
            if not columns:
                return f"Model '{model_name}' not found."

            lines = [f"Model: {model_name}", ""]
            lines.append("Columns:")
            for col in columns:
                pk = " (PK)" if col.is_primary_key else ""
                nullable = " NULL" if col.is_nullable else " NOT NULL"
                lines.append(f"  - {col.name}: {col.data_type}{pk}{nullable}")

            return "\n".join(lines)
        except Exception as e:
            return f"Error: {e}"

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
            return "Usage: /dbt show <model_name>"
        return self._run_dbt_command(["show", "--select", model])

    def _run_dbt_command(
        self,
        command: list[str],
        select: str | None = None,
    ) -> str:
        """Run a dbt CLI command.

        Args:
            command: dbt command arguments.
            select: Optional model selection.

        Returns:
            Command output.
        """
        full_command = ["dbt"] + command

        if select:
            full_command.extend(["--select", select])

        full_command.extend([
            "--project-dir",
            str(self.agent.dbt_project_dir),
        ])

        if self.agent.dbt_profiles_dir:
            full_command.extend([
                "--profiles-dir",
                str(self.agent.dbt_profiles_dir),
            ])

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
                return f"Error:\n{result.stderr or result.stdout}"

        except subprocess.TimeoutExpired:
            return "Command timed out after 5 minutes."
        except FileNotFoundError:
            return "dbt command not found. Ensure dbt is installed."
        except Exception as e:
            return f"Error: {e}"
