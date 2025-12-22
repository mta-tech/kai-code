"""DbtAgent - specialized agent for dbt data engineering."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from kai_code.agent import KaiAgent
from kai_code.agents.dbt.adapters import DatabaseAdapter, get_adapter
from kai_code.agents.dbt.tools.dbt_cli_tools import create_dbt_cli_tools
from kai_code.agents.dbt.tools.schema_tools import create_schema_tools


class DbtAgent(KaiAgent):
    """Specialized agent for dbt data engineering.

    Inherits ALL KaiAgent capabilities:
    - File operations (read, write, edit, glob, grep)
    - Shell execution (execute)
    - Patch application (apply_patch)
    - Skills system (.skills/)
    - YOLO/approval modes
    - Session persistence

    Adds dbt-specific capabilities:
    - Schema introspection tools
    - dbt CLI wrapper tools
    - Database adapter connection
    - dbt skill auto-loading
    """

    def __init__(
        self,
        root_dir: str | Path,
        *,
        model: str | None = None,
        db_connection: str | None = None,
        dbt_project_dir: str | Path | None = None,
        dbt_profiles_dir: str | Path | None = None,
        yolo: bool = True,
        system_prompt: str | None = None,
        skills_dir: str = ".skills",
        state_path: str | Path | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize DbtAgent.

        Args:
            root_dir: Project root directory.
            model: LLM model handle.
            db_connection: Database connection string for introspection.
            dbt_project_dir: dbt project directory (defaults to root_dir).
            dbt_profiles_dir: profiles.yml location (defaults to ~/.dbt).
            yolo: If False, require approval for dbt commands.
            system_prompt: Additional system prompt.
            skills_dir: Skills directory.
            state_path: Session state file path.
            **kwargs: Additional KaiAgent arguments.
        """
        # Build enhanced system prompt with dbt context
        dbt_prompt = self._build_dbt_system_prompt()
        combined_prompt = (
            f"{dbt_prompt}\n\n{system_prompt}" if system_prompt else dbt_prompt
        )

        # Initialize parent KaiAgent
        super().__init__(
            root_dir=root_dir,
            model=model,
            yolo=yolo,
            system_prompt=combined_prompt,
            skills_dir=skills_dir,
            state_path=state_path,
            **kwargs,
        )

        # dbt-specific configuration
        self._db_connection = db_connection
        self._dbt_project_dir = (
            Path(dbt_project_dir) if dbt_project_dir else Path(root_dir)
        )
        self._dbt_profiles_dir = Path(dbt_profiles_dir) if dbt_profiles_dir else None
        self._adapter: DatabaseAdapter | None = None

        # Initialize database adapter if connection provided
        if db_connection:
            self._adapter = get_adapter(db_connection)

    @property
    def adapter(self) -> DatabaseAdapter | None:
        """Database adapter for introspection."""
        return self._adapter

    @property
    def db_connection(self) -> str | None:
        """Database connection string."""
        return self._db_connection

    @property
    def dbt_project_dir(self) -> Path:
        """dbt project directory."""
        return self._dbt_project_dir

    @property
    def dbt_profiles_dir(self) -> Path | None:
        """dbt profiles directory."""
        return self._dbt_profiles_dir

    def _build_dbt_system_prompt(self) -> str:
        """Build dbt-specific system prompt content."""
        return """## dbt Data Engineering Agent

You are a data engineer specializing in dbt. You build production-quality data pipelines.

### Before Implementation
1. Use get_database_schema() to explore available tables
2. Read dbt_docs/ files for detailed dbt documentation
3. Use get_instructions() if available for business rules

### Layer Conventions
- **staging/** (stg_): Views, 1:1 with source, cleaning only
- **intermediate/** (int_): Tables, business logic, not user-facing
- **marts/** (fct_, dim_): Tables, analytics-ready

### Model Checklist
- Config block with materialization
- CTEs for organization
- Explicit column selection (no SELECT *)
- Data type casting
- Tests in schema.yml
"""

    def get_dbt_tools(self) -> list:
        """Get all dbt-specific tools.

        Returns:
            List of LangChain tools.
        """
        tools = []

        # Schema tools (require adapter)
        if self._adapter:
            tools.extend(create_schema_tools(self._adapter))

        # dbt CLI tools
        tools.extend(
            create_dbt_cli_tools(
                self._dbt_project_dir,
                self._dbt_profiles_dir,
            )
        )

        return tools
