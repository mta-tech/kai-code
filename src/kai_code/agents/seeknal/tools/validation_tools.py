"""Seeknal validation tools."""

import sys
from pathlib import Path
from langchain_core.tools import tool


def create_validation_tools(seeknal_path: Path) -> list:
    """Create validation tools.

    Args:
        seeknal_path: Path to Seeknal library.

    Returns:
        List of LangChain tools.
    """
    seeknal_src = seeknal_path / "src"

    @tool("seeknal_validate_sql_identifier")
    def seeknal_validate_sql_identifier(identifier: str) -> str:
        """Validate a SQL identifier to prevent injection.

        Args:
            identifier: SQL identifier to validate.

        Returns:
            Validation result.
        """
        import json

        try:
            sys.path.insert(0, str(seeknal_src))

            from seeknal.validation import validate_sql_identifier

            validate_sql_identifier(identifier)

            return json.dumps({
                "status": "success",
                "message": f"Identifier '{identifier}' is valid",
                "identifier": identifier,
            }, indent=2)
        except Exception as e:
            return json.dumps({
                "status": "error",
                "message": str(e),
                "identifier": identifier,
            }, indent=2)

    @tool("seeknal_validate_table_name")
    def seeknal_validate_table_name(table_name: str) -> str:
        """Validate a table name to prevent injection.

        Args:
            table_name: Table name to validate.

        Returns:
            Validation result.
        """
        import json

        try:
            sys.path.insert(0, str(seeknal_src))

            from seeknal.validation import validate_table_name

            validate_table_name(table_name)

            return json.dumps({
                "status": "success",
                "message": f"Table name '{table_name}' is valid",
                "table_name": table_name,
            }, indent=2)
        except Exception as e:
            return json.dumps({
                "status": "error",
                "message": str(e),
                "table_name": table_name,
            }, indent=2)

    @tool("seeknal_validate_column_name")
    def seeknal_validate_column_name(column_name: str) -> str:
        """Validate a column name to prevent injection.

        Args:
            column_name: Column name to validate.

        Returns:
            Validation result.
        """
        import json

        try:
            sys.path.insert(0, str(seeknal_src))

            from seeknal.validation import validate_column_name

            validate_column_name(column_name)

            return json.dumps({
                "status": "success",
                "message": f"Column name '{column_name}' is valid",
                "column_name": column_name,
            }, indent=2)
        except Exception as e:
            return json.dumps({
                "status": "error",
                "message": str(e),
                "column_name": column_name,
            }, indent=2)

    @tool("seeknal_validate_file_path")
    def seeknal_validate_file_path(file_path: str) -> str:
        """Validate a file path for security.

        Args:
            file_path: File path to validate.

        Returns:
            Validation result.
        """
        import json

        try:
            sys.path.insert(0, str(seeknal_src))

            from seeknal.validation import validate_file_path

            validate_file_path(file_path)

            return json.dumps({
                "status": "success",
                "message": f"File path '{file_path}' is valid",
                "file_path": file_path,
            }, indent=2)
        except Exception as e:
            return json.dumps({
                "status": "error",
                "message": str(e),
                "file_path": file_path,
            }, indent=2)

    @tool("seeknal_validate_features")
    def seeknal_validate_features(
        feature_group: str,
        mode: str = "warn",
    ) -> str:
        """Validate features in a feature group.

        Args:
            feature_group: Feature group name.
            mode: Validation mode (warn or fail).

        Returns:
            Validation result.
        """
        import json
        import subprocess

        try:
            # Use seeknal CLI
            result = subprocess.run(
                [
                    "seeknal", "validate-features", feature_group,
                    "--mode", mode
                ],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=str(seeknal_path),
            )

            if result.returncode == 0:
                return json.dumps({
                    "status": "success",
                    "validation": result.stdout.strip(),
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
        seeknal_validate_sql_identifier,
        seeknal_validate_table_name,
        seeknal_validate_column_name,
        seeknal_validate_file_path,
        seeknal_validate_features,
    ]
