"""Seeknal feature store management tools."""

import sys
from pathlib import Path
from langchain_core.tools import tool


def create_feature_store_tools(seeknal_path: Path) -> list:
    """Create feature store tools.

    Args:
        seeknal_path: Path to Seeknal library.

    Returns:
        List of LangChain tools.
    """
    seeknal_src = seeknal_path / "src"

    @tool("seeknal_create_feature_group")
    def seeknal_create_feature_group(
        name: str,
        entity_name: str,
        entity_join_keys: str,
        project: str,
        event_time_col: str = "timestamp",
        engine: str = "duckdb",
    ) -> str:
        """Create a new feature group.

        Args:
            name: Feature group name.
            entity_name: Entity name.
            entity_join_keys: Comma-separated join keys (e.g., "user_id").
            project: Project name.
            event_time_col: Event time column name.
            engine: Engine to use (duckdb or spark).

        Returns:
            Result message.
        """
        import json

        try:
            sys.path.insert(0, str(seeknal_src))

            from seeknal.entity import Entity
            from seeknal.featurestore.duckdbengine.feature_group import (
                FeatureGroupDuckDB,
                Materialization,
            )

            # Parse join keys
            join_keys = [k.strip() for k in entity_join_keys.split(",")]

            # Create entity
            entity = Entity(name=entity_name, join_keys=join_keys).get_or_create()

            # Create materialization
            materialization = Materialization(
                event_time_col=event_time_col,
                offline=True,
            )

            # Create feature group
            fg = FeatureGroupDuckDB(
                name=name,
                entity=entity,
                materialization=materialization,
                project=project,
            )
            fg.get_or_create()

            return json.dumps({
                "status": "success",
                "message": f"Feature group '{name}' created successfully",
                "feature_group": {
                    "name": name,
                    "entity": entity_name,
                    "join_keys": join_keys,
                    "project": project,
                    "engine": engine,
                }
            }, indent=2)
        except Exception as e:
            return json.dumps({
                "status": "error",
                "message": str(e)
            }, indent=2)

    @tool("seeknal_list_feature_groups")
    def seeknal_list_feature_groups() -> str:
        """List all feature groups.

        Returns:
            JSON list of feature groups.
        """
        import json
        import subprocess

        try:
            # Use seeknal CLI
            result = subprocess.run(
                ["seeknal", "list", "feature-groups"],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=str(seeknal_path),
            )

            if result.returncode == 0:
                return json.dumps({
                    "status": "success",
                    "feature_groups": result.stdout.strip(),
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

    @tool("seeknal_delete_feature_group")
    def seeknal_delete_feature_group(name: str) -> str:
        """Delete a feature group.

        Args:
            name: Feature group name.

        Returns:
            Result message.
        """
        import json
        import subprocess

        try:
            # Use seeknal CLI
            result = subprocess.run(
                ["seeknal", "delete", "feature-group", name],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=str(seeknal_path),
            )

            if result.returncode == 0:
                return json.dumps({
                    "status": "success",
                    "message": f"Feature group '{name}' deleted successfully",
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

    @tool("seeknal_materialize_features")
    def seeknal_materialize_features(
        name: str,
        start_date: str,
        version: int | None = None,
    ) -> str:
        """Materialize features to offline store.

        Args:
            name: Feature group name.
            start_date: Start date (YYYY-MM-DD format).
            version: Feature group version (defaults to latest).

        Returns:
            Result message.
        """
        import json
        from datetime import datetime

        try:
            sys.path.insert(0, str(seeknal_src))

            from seeknal.featurestore.duckdbengine.feature_group import FeatureGroupDuckDB

            # Parse date
            feature_start_time = datetime.strptime(start_date, "%Y-%m-%d")

            # Get feature group
            fg = FeatureGroupDuckDB(name=name).get_or_create()

            # Materialize
            if version:
                fg.write(feature_start_time=feature_start_time, version=version)
            else:
                fg.write(feature_start_time=feature_start_time)

            return json.dumps({
                "status": "success",
                "message": f"Feature group '{name}' materialized successfully",
                "materialization": {
                    "name": name,
                    "start_date": start_date,
                    "version": version,
                }
            }, indent=2)
        except Exception as e:
            return json.dumps({
                "status": "error",
                "message": str(e)
            }, indent=2)

    return [
        seeknal_create_feature_group,
        seeknal_list_feature_groups,
        seeknal_delete_feature_group,
        seeknal_materialize_features,
    ]
