"""Configuration loader for kai-dbt CLI."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore


@dataclass
class DbtCliConfig:
    """Configuration for kai-dbt CLI.

    Priority (highest to lowest):
    1. CLI arguments
    2. Environment variables
    3. Config file (.kai/dbt.yaml)
    4. Defaults
    """

    connection: str | None = None
    profile: str | None = None
    target: str | None = None
    docs_dir: str | None = None
    schema: str | None = None
    env: str = "default"
    project_dir: Path | None = None

    def merge_with(self, other: dict[str, Any]) -> "DbtCliConfig":
        """Merge with another config, other takes priority for non-None values.

        Args:
            other: Dictionary of config values to merge.

        Returns:
            New DbtCliConfig with merged values.
        """
        return DbtCliConfig(
            connection=other.get("connection") or self.connection,
            profile=other.get("profile") or self.profile,
            target=other.get("target") or self.target,
            docs_dir=other.get("docs_dir") or self.docs_dir,
            schema=other.get("schema") or self.schema,
            env=other.get("env") or self.env,
            project_dir=other.get("project_dir") or self.project_dir,
        )


@dataclass
class DbtProjectInfo:
    """Information about a detected dbt project."""

    project_dir: Path
    project_name: str
    profile: str | None = None
    model_paths: list[str] = field(default_factory=lambda: ["models"])
    version: str | None = None


def _load_config_file(config_path: Path, env: str) -> dict[str, Any]:
    """Load configuration from YAML file.

    Args:
        config_path: Path to dbt.yaml config file.
        env: Environment name to load.

    Returns:
        Dictionary with configuration values.
    """
    if yaml is None:
        return {}

    if not config_path.exists():
        return {}

    try:
        with open(config_path) as f:
            data = yaml.safe_load(f) or {}

        # Get environment-specific config
        env_config = data.get(env, {})
        if isinstance(env_config, dict):
            return env_config
        return {}
    except Exception:
        return {}


def _get_env_overrides() -> dict[str, Any]:
    """Get configuration from environment variables.

    Environment variables:
    - KAI_DBT_CONNECTION: Database connection string
    - KAI_DBT_PROFILE: dbt profile name
    - KAI_DBT_TARGET: dbt target
    - KAI_DBT_DOCS_DIR: Documentation directory
    - KAI_DBT_SCHEMA: Default schema

    Returns:
        Dictionary with environment variable values.
    """
    overrides: dict[str, Any] = {}

    env_map = {
        "KAI_DBT_CONNECTION": "connection",
        "KAI_DBT_PROFILE": "profile",
        "KAI_DBT_TARGET": "target",
        "KAI_DBT_DOCS_DIR": "docs_dir",
        "KAI_DBT_SCHEMA": "schema",
    }

    for env_var, key in env_map.items():
        value = os.environ.get(env_var)
        if value:
            overrides[key] = value

    return overrides


def load_config(
    project_dir: Path | str | None = None,
    env: str | None = None,
    cli_overrides: dict[str, Any] | None = None,
) -> DbtCliConfig:
    """Load dbt CLI configuration with proper priority.

    Priority (highest to lowest):
    1. CLI arguments (cli_overrides)
    2. Environment variables
    3. Config file (.kai/dbt.yaml)
    4. Defaults

    Args:
        project_dir: Project directory containing .kai/dbt.yaml.
        env: Configuration environment name.
        cli_overrides: CLI argument overrides.

    Returns:
        Merged DbtCliConfig instance.
    """
    # Determine project directory
    if project_dir is None:
        project_dir = Path.cwd()
    else:
        project_dir = Path(project_dir)

    # Determine environment (check env var if not specified)
    if env is None:
        env = os.environ.get("KAI_DBT_ENV", "default")

    # Start with defaults
    config = DbtCliConfig(env=env, project_dir=project_dir)

    # Load from config file
    config_path = project_dir / ".kai" / "dbt.yaml"
    file_config = _load_config_file(config_path, env)
    if file_config:
        config = config.merge_with(file_config)

    # Apply environment variable overrides
    env_overrides = _get_env_overrides()
    if env_overrides:
        config = config.merge_with(env_overrides)

    # Apply CLI overrides (highest priority)
    if cli_overrides:
        # Filter out None values from CLI overrides
        filtered_overrides = {k: v for k, v in cli_overrides.items() if v is not None}
        if filtered_overrides:
            config = config.merge_with(filtered_overrides)

    return config


def find_dbt_project(start_dir: Path | str | None = None) -> DbtProjectInfo | None:
    """Find dbt project by searching for dbt_project.yml.

    Searches current directory and parent directories up to filesystem root.

    Args:
        start_dir: Directory to start search from (defaults to cwd).

    Returns:
        DbtProjectInfo if found, None otherwise.
    """
    if yaml is None:
        return None

    if start_dir is None:
        start_dir = Path.cwd()
    else:
        start_dir = Path(start_dir)

    current = start_dir.resolve()

    while current != current.parent:
        project_file = current / "dbt_project.yml"

        if project_file.exists():
            try:
                with open(project_file) as f:
                    data = yaml.safe_load(f) or {}

                return DbtProjectInfo(
                    project_dir=current,
                    project_name=data.get("name", "unknown"),
                    profile=data.get("profile"),
                    model_paths=data.get("model-paths", ["models"]),
                    version=data.get("version"),
                )
            except Exception:
                return None

        current = current.parent

    return None
