"""Seeknal project management tools."""

import sys
from pathlib import Path
from langchain_core.tools import tool


def create_project_tools(seeknal_path: Path) -> list:
    """Create project management tools.

    Args:
        seeknal_path: Path to Seeknal library.

    Returns:
        List of LangChain tools.
    """
    seeknal_src = seeknal_path / "src"

    @tool("seeknal_init_project")
    def seeknal_init_project(
        name: str,
        description: str = "",
    ) -> str:
        """Initialize a new Seeknal project.

        Args:
            name: Project name.
            description: Project description.

        Returns:
            Result message.
        """
        import json
        import subprocess

        try:
            # Add seeknal to path
            sys.path.insert(0, str(seeknal_src))

            from seeknal.project import Project

            project = Project(name=name, description=description)
            project.get_or_create()

            return json.dumps({
                "status": "success",
                "message": f"Project '{name}' created successfully",
                "project": {
                    "name": name,
                    "description": description,
                }
            }, indent=2)
        except Exception as e:
            return json.dumps({
                "status": "error",
                "message": str(e)
            }, indent=2)

    @tool("seeknal_list_projects")
    def seeknal_list_projects() -> str:
        """List all Seeknal projects.

        Returns:
            JSON list of projects.
        """
        import json
        import subprocess

        try:
            # Use seeknal CLI
            result = subprocess.run(
                ["seeknal", "list", "projects"],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=str(seeknal_path),
            )

            if result.returncode == 0:
                return json.dumps({
                    "status": "success",
                    "projects": result.stdout.strip(),
                }, indent=2)
            else:
                return json.dumps({
                    "status": "error",
                    "message": result.stderr or result.stdout
                }, indent=2)
        except Exception as e:
            return json.dumps({
                "status": "error",
                "message": str(e)
            }, indent=2)

    @tool("seeknal_get_project")
    def seeknal_get_project(name: str) -> str:
        """Get project details.

        Args:
            name: Project name.

        Returns:
            Project details.
        """
        import json

        try:
            sys.path.insert(0, str(seeknal_src))

            from seeknal.project import Project

            project = Project(name=name).get_or_create()

            return json.dumps({
                "status": "success",
                "project": {
                    "name": project.name,
                    "description": project.description,
                    "id": project.id,
                }
            }, indent=2)
        except Exception as e:
            return json.dumps({
                "status": "error",
                "message": str(e)
            }, indent=2)

    @tool("seeknal_delete_project")
    def seeknal_delete_project(name: str) -> str:
        """Delete a Seeknal project.

        Args:
            name: Project name.

        Returns:
            Result message.
        """
        import json
        import subprocess

        try:
            # Use seeknal CLI
            result = subprocess.run(
                ["seeknal", "delete", "project", name],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=str(seeknal_path),
            )

            if result.returncode == 0:
                return json.dumps({
                    "status": "success",
                    "message": f"Project '{name}' deleted successfully",
                }, indent=2)
            else:
                return json.dumps({
                    "status": "error",
                    "message": result.stderr or result.stdout
                }, indent=2)
        except Exception as e:
            return json.dumps({
                "status": "error",
                "message": str(e)
            }, indent=2)

    return [
        seeknal_init_project,
        seeknal_list_projects,
        seeknal_get_project,
        seeknal_delete_project,
    ]
