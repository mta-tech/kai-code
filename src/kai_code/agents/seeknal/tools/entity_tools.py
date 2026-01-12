"""Seeknal entity management tools."""

import sys
from pathlib import Path
from langchain_core.tools import tool


def create_entity_tools(seeknal_path: Path) -> list:
    """Create entity management tools.

    Args:
        seeknal_path: Path to Seeknal library.

    Returns:
        List of LangChain tools.
    """
    seeknal_src = seeknal_path / "src"

    @tool("seeknal_create_entity")
    def seeknal_create_entity(
        name: str,
        join_keys: str,
    ) -> str:
        """Create a new entity.

        Args:
            name: Entity name.
            join_keys: Comma-separated join keys (e.g., "user_id,account_id").

        Returns:
            Result message.
        """
        import json

        try:
            sys.path.insert(0, str(seeknal_src))

            from seeknal.entity import Entity

            # Parse join keys
            keys = [k.strip() for k in join_keys.split(",")]

            # Create entity
            entity = Entity(name=name, join_keys=keys).get_or_create()

            return json.dumps({
                "status": "success",
                "message": f"Entity '{name}' created successfully",
                "entity": {
                    "name": name,
                    "join_keys": keys,
                    "id": entity.id,
                }
            }, indent=2)
        except Exception as e:
            return json.dumps({
                "status": "error",
                "message": str(e)
            }, indent=2)

    @tool("seeknal_list_entities")
    def seeknal_list_entities() -> str:
        """List all entities.

        Returns:
            JSON list of entities.
        """
        import json
        import subprocess

        try:
            # Use seeknal CLI
            result = subprocess.run(
                ["seeknal", "list", "entities"],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=str(seeknal_path),
            )

            if result.returncode == 0:
                return json.dumps({
                    "status": "success",
                    "entities": result.stdout.strip(),
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

    @tool("seeknal_get_entity")
    def seeknal_get_entity(name: str) -> str:
        """Get entity details.

        Args:
            name: Entity name.

        Returns:
            Entity details.
        """
        import json

        try:
            sys.path.insert(0, str(seeknal_src))

            from seeknal.entity import Entity

            entity = Entity(name=name).get_or_create()

            return json.dumps({
                "status": "success",
                "entity": {
                    "name": entity.name,
                    "join_keys": entity.join_keys,
                    "id": entity.id,
                }
            }, indent=2)
        except Exception as e:
            return json.dumps({
                "status": "error",
                "message": str(e)
            }, indent=2)

    return [
        seeknal_create_entity,
        seeknal_list_entities,
        seeknal_get_entity,
    ]
