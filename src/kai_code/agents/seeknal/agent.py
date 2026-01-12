"""SeeknalAgent - specialized agent for data engineering and data science."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from kai_code.agent import KaiAgent


class SeeknalAgent(KaiAgent):
    """Specialized agent for data engineering and data science using Seeknal.

    Inherits ALL KaiAgent capabilities:
    - File operations (read, write, edit, glob, grep)
    - Shell execution (execute)
    - Patch application (apply_patch)
    - Skills system (.skills/)
    - YOLO/approval modes
    - Session persistence

    Adds Seeknal-specific capabilities:
    - Feature store management (offline/online)
    - Data pipeline orchestration (Flow)
    - Entity and project management
    - Feature group versioning
    - DuckDB and Spark engine operations
    - Data validation
    """

    def __init__(
        self,
        root_dir: str | Path,
        *,
        model: str | None = None,
        seeknal_path: str | Path | None = None,
        yolo: bool = True,
        system_prompt: str | None = None,
        skills_dir: str = ".skills",
        state_path: str | Path | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize SeeknalAgent.

        Args:
            root_dir: Project root directory.
            model: LLM model handle.
            seeknal_path: Path to Seeknal library (defaults to ~/project/mta/signal).
            yolo: If False, require approval for destructive operations.
            system_prompt: Additional system prompt.
            skills_dir: Skills directory.
            state_path: Session state file path.
            **kwargs: Additional KaiAgent arguments.
        """
        # Initialize parent KaiAgent
        super().__init__(
            root_dir=root_dir,
            model=model,
            yolo=yolo,
            system_prompt=system_prompt,
            skills_dir=skills_dir,
            state_path=state_path,
            **kwargs,
        )

        # Seeknal-specific configuration
        if seeknal_path is None:
            seeknal_path = Path.home() / "project" / "mta" / "signal"
        self._seeknal_path = Path(seeknal_path)

    @property
    def seeknal_path(self) -> Path:
        """Path to Seeknal library."""
        return self._seeknal_path

    def _get_base_prompt_name(self) -> str:
        """Use kai-seeknal prompt (inherits from kai-code)."""
        return "kai-seeknal"

    def get_seeknal_tools(self) -> list:
        """Get all Seeknal-specific tools.

        Returns:
            List of LangChain tools.
        """
        from kai_code.agents.seeknal.tools.project_tools import create_project_tools
        from kai_code.agents.seeknal.tools.flow_tools import create_flow_tools
        from kai_code.agents.seeknal.tools.feature_store_tools import create_feature_store_tools
        from kai_code.agents.seeknal.tools.entity_tools import create_entity_tools
        from kai_code.agents.seeknal.tools.version_tools import create_version_tools
        from kai_code.agents.seeknal.tools.validation_tools import create_validation_tools

        tools = []

        # Project management tools
        tools.extend(create_project_tools(self._seeknal_path))

        # Flow/pipeline tools
        tools.extend(create_flow_tools(self._seeknal_path))

        # Feature store tools
        tools.extend(create_feature_store_tools(self._seeknal_path))

        # Entity tools
        tools.extend(create_entity_tools(self._seeknal_path))

        # Version management tools
        tools.extend(create_version_tools(self._seeknal_path))

        # Validation tools
        tools.extend(create_validation_tools(self._seeknal_path))

        return tools

    def _get_subclass_tools(self) -> list:
        """Add Seeknal-specific tools to the agent.

        Returns:
            List of Seeknal-specific LangChain tools.
        """
        return self.get_seeknal_tools()
