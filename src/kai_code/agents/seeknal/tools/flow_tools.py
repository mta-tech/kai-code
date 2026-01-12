"""Seeknal flow/pipeline management tools."""

import sys
from pathlib import Path
from langchain_core.tools import tool


def create_flow_tools(seeknal_path: Path) -> list:
    """Create flow/pipeline tools.

    Args:
        seeknal_path: Path to Seeknal library.

    Returns:
        List of LangChain tools.
    """
    seeknal_src = seeknal_path / "src"

    @tool("seeknal_create_flow")
    def seeknal_create_flow(
        name: str,
        project: str,
        input_kind: str,
        input_value: str,
        tasks: str,
    ) -> str:
        """Create a new Seeknal flow (data pipeline).

        Args:
            name: Flow name.
            project: Project name.
            input_kind: Input type (PARQUET, HIVE_TABLE, SPARK_DATAFRAME, etc.).
            input_value: Input value (file path or table name).
            tasks: JSON string of task definitions.

        Returns:
            Result message.
        """
        import json

        try:
            sys.path.insert(0, str(seeknal_src))

            from seeknal.project import Project
            from seeknal.flow import Flow, FlowInput, FlowOutput, FlowInputEnum
            from seeknal.tasks.duckdb import DuckDBTask

            # Get project
            project_obj = Project(name=project).get_or_create()

            # Parse tasks
            task_list = json.loads(tasks)

            # Create tasks
            flow_tasks = []
            for task_def in task_list:
                if task_def.get("type") == "duckdb":
                    task = DuckDBTask()
                    if "sql" in task_def:
                        task = task.add_sql(task_def["sql"])
                    flow_tasks.append(task)

            # Create flow input
            flow_input = FlowInput(
                kind=FlowInputEnum[input_kind.upper()],
                value=input_value
            )

            # Create flow
            flow = Flow(
                name=name,
                input=flow_input,
                tasks=flow_tasks,
                output=FlowOutput(),
            )
            flow.get_or_create()

            return json.dumps({
                "status": "success",
                "message": f"Flow '{name}' created successfully",
                "flow": {
                    "name": name,
                    "project": project,
                    "input": {"kind": input_kind, "value": input_value},
                    "tasks_count": len(flow_tasks),
                }
            }, indent=2)
        except Exception as e:
            return json.dumps({
                "status": "error",
                "message": str(e)
            }, indent=2)

    @tool("seeknal_run_flow")
    def seeknal_run_flow(name: str) -> str:
        """Run a Seeknal flow.

        Args:
            name: Flow name.

        Returns:
            Result message.
        """
        import json

        try:
            sys.path.insert(0, str(seeknal_src))

            from seeknal.flow import Flow

            flow = Flow(name=name).get_or_create()
            result = flow.run()

            return json.dumps({
                "status": "success",
                "message": f"Flow '{name}' executed successfully",
                "result": str(result),
            }, indent=2)
        except Exception as e:
            return json.dumps({
                "status": "error",
                "message": str(e)
            }, indent=2)

    @tool("seeknal_list_flows")
    def seeknal_list_flows() -> str:
        """List all Seeknal flows.

        Returns:
            JSON list of flows.
        """
        import json
        import subprocess

        try:
            # Use seeknal CLI
            result = subprocess.run(
                ["seeknal", "list", "flows"],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=str(seeknal_path),
            )

            if result.returncode == 0:
                return json.dumps({
                    "status": "success",
                    "flows": result.stdout.strip(),
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
        seeknal_create_flow,
        seeknal_run_flow,
        seeknal_list_flows,
    ]
