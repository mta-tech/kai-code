"""dbt CLI wrapper tools for DbtAgent."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from langchain_core.tools import tool


def _run_dbt_command(
    command: list[str],
    project_dir: Path,
    profiles_dir: Path | None = None,
) -> dict[str, Any]:
    """Run a dbt command and return parsed result.

    Args:
        command: dbt command arguments.
        project_dir: Path to dbt project.
        profiles_dir: Optional path to profiles directory.

    Returns:
        Dictionary with success status and output.
    """
    full_command = ["dbt"] + command + ["--project-dir", str(project_dir)]

    if profiles_dir:
        full_command.extend(["--profiles-dir", str(profiles_dir)])

    try:
        result = subprocess.run(
            full_command,
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout
            cwd=str(project_dir),
        )

        return {
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "stdout": "",
            "stderr": "Command timed out after 5 minutes",
            "returncode": -1,
        }
    except FileNotFoundError:
        return {
            "success": False,
            "stdout": "",
            "stderr": "dbt command not found. Ensure dbt is installed.",
            "returncode": -1,
        }
    except Exception as e:
        return {
            "success": False,
            "stdout": "",
            "stderr": str(e),
            "returncode": -1,
        }


def create_dbt_cli_tools(
    project_dir: Path | str,
    profiles_dir: Path | str | None = None,
) -> list:
    """Create dbt CLI wrapper tools.

    Args:
        project_dir: Path to dbt project directory.
        profiles_dir: Optional path to profiles.yml directory.

    Returns:
        List of LangChain tools.
    """
    project_dir = Path(project_dir)
    profiles_dir = Path(profiles_dir) if profiles_dir else None

    @tool("dbt_run")
    def dbt_run(
        select: str | None = None,
        exclude: str | None = None,
        full_refresh: bool = False,
    ) -> str:
        """Run dbt models.

        Args:
            select: Model selection (e.g., '+my_model', 'tag:staging').
            exclude: Models to exclude.
            full_refresh: Force full refresh of incremental models.

        Returns:
            JSON with run results.
        """
        command = ["run"]

        if select:
            command.extend(["--select", select])
        if exclude:
            command.extend(["--exclude", exclude])
        if full_refresh:
            command.append("--full-refresh")

        result = _run_dbt_command(command, project_dir, profiles_dir)

        if result["success"]:
            # Parse output for model counts
            output = result["stdout"]
            return json.dumps(
                {
                    "success": True,
                    "message": "dbt run completed successfully",
                    "output": output,
                },
                indent=2,
            )
        else:
            return json.dumps(
                {
                    "success": False,
                    "error": result["stderr"] or result["stdout"],
                    "suggestion": "Check model syntax and dependencies",
                },
                indent=2,
            )

    @tool("dbt_test")
    def dbt_test(select: str | None = None) -> str:
        """Run dbt tests.

        Args:
            select: Test selection criteria.

        Returns:
            JSON with test results.
        """
        command = ["test"]

        if select:
            command.extend(["--select", select])

        result = _run_dbt_command(command, project_dir, profiles_dir)

        return json.dumps(
            {
                "success": result["success"],
                "output": result["stdout"],
                "error": result["stderr"] if not result["success"] else None,
            },
            indent=2,
        )

    @tool("dbt_compile")
    def dbt_compile(model_name: str | None = None) -> str:
        """Compile dbt models and return generated SQL.

        Args:
            model_name: Specific model to compile.

        Returns:
            JSON with compiled SQL.
        """
        command = ["compile"]

        if model_name:
            command.extend(["--select", model_name])

        result = _run_dbt_command(command, project_dir, profiles_dir)

        return json.dumps(
            {
                "success": result["success"],
                "output": result["stdout"],
                "error": result["stderr"] if not result["success"] else None,
            },
            indent=2,
        )

    @tool("dbt_list")
    def dbt_list(
        select: str | None = None,
        resource_type: str | None = None,
    ) -> str:
        """List dbt resources.

        Args:
            select: Selection criteria.
            resource_type: Filter by type (model, test, source, seed, snapshot).

        Returns:
            JSON with resource list.
        """
        command = ["list"]

        if select:
            command.extend(["--select", select])
        if resource_type:
            command.extend(["--resource-type", resource_type])

        result = _run_dbt_command(command, project_dir, profiles_dir)

        if result["success"]:
            resources = [
                r.strip() for r in result["stdout"].strip().split("\n") if r.strip()
            ]
            return json.dumps(
                {
                    "success": True,
                    "resources": resources,
                    "count": len(resources),
                },
                indent=2,
            )
        else:
            return json.dumps(
                {
                    "success": False,
                    "error": result["stderr"] or result["stdout"],
                },
                indent=2,
            )

    @tool("dbt_show")
    def dbt_show(model_name: str, limit: int = 10) -> str:
        """Preview model output.

        Args:
            model_name: Model to preview.
            limit: Number of rows to show.

        Returns:
            JSON with sample data.
        """
        command = ["show", "--select", model_name, "--limit", str(limit)]

        result = _run_dbt_command(command, project_dir, profiles_dir)

        return json.dumps(
            {
                "success": result["success"],
                "output": result["stdout"],
                "error": result["stderr"] if not result["success"] else None,
            },
            indent=2,
        )

    return [dbt_run, dbt_test, dbt_compile, dbt_list, dbt_show]
