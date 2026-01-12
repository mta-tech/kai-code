"""Seeknal version management tools."""

import sys
from pathlib import Path
from langchain_core.tools import tool


def create_version_tools(seeknal_path: Path) -> list:
    """Create version management tools.

    Args:
        seeknal_path: Path to Seeknal library.

    Returns:
        List of LangChain tools.
    """
    seeknal_src = seeknal_path / "src"

    @tool("seeknal_list_versions")
    def seeknal_list_versions(
        feature_group: str,
        limit: int = 10,
    ) -> str:
        """List all versions of a feature group.

        Args:
            feature_group: Feature group name.
            limit: Maximum number of versions to return.

        Returns:
            JSON list of versions.
        """
        import json
        import subprocess

        try:
            # Use seeknal CLI
            cmd = ["seeknal", "version", "list", feature_group]
            if limit:
                cmd.extend(["--limit", str(limit)])

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                cwd=str(seeknal_path),
            )

            if result.returncode == 0:
                return json.dumps({
                    "status": "success",
                    "versions": result.stdout.strip(),
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

    @tool("seeknal_show_version")
    def seeknal_show_version(
        feature_group: str,
        version: int | None = None,
    ) -> str:
        """Show details of a specific version.

        Args:
            feature_group: Feature group name.
            version: Version number (defaults to latest).

        Returns:
            Version details.
        """
        import json
        import subprocess

        try:
            # Use seeknal CLI
            cmd = ["seeknal", "version", "show", feature_group]
            if version:
                cmd.extend(["--version", str(version)])

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                cwd=str(seeknal_path),
            )

            if result.returncode == 0:
                return json.dumps({
                    "status": "success",
                    "version": result.stdout.strip(),
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

    @tool("seeknal_compare_versions")
    def seeknal_compare_versions(
        feature_group: str,
        from_version: int,
        to_version: int,
    ) -> str:
        """Compare two versions of a feature group.

        Args:
            feature_group: Feature group name.
            from_version: First version number.
            to_version: Second version number.

        Returns:
            Version comparison.
        """
        import json
        import subprocess

        try:
            # Use seeknal CLI
            result = subprocess.run(
                [
                    "seeknal", "version", "diff", feature_group,
                    "--from", str(from_version),
                    "--to", str(to_version)
                ],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=str(seeknal_path),
            )

            if result.returncode == 0:
                return json.dumps({
                    "status": "success",
                    "comparison": result.stdout.strip(),
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
        seeknal_list_versions,
        seeknal_show_version,
        seeknal_compare_versions,
    ]
