"""Tests for dbt CLI configuration loader."""
import pytest
import os
from pathlib import Path

from kai_code.agents.dbt.config import DbtCliConfig, load_config


@pytest.fixture
def config_dir(tmp_path):
    """Create a .kai directory with dbt.yaml config."""
    kai_dir = tmp_path / ".kai"
    kai_dir.mkdir()

    config_content = """
default:
  connection: analytics.duckdb
  profile: dev

production:
  connection: postgresql://prod-db/analytics
  profile: prod
  target: prod
"""
    (kai_dir / "dbt.yaml").write_text(config_content)
    return tmp_path


def test_dbt_cli_config_defaults():
    """DbtCliConfig has sensible defaults."""
    config = DbtCliConfig()
    assert config.connection is None
    assert config.profile is None
    assert config.target is None
    assert config.env == "default"


def test_load_config_from_file(config_dir):
    """load_config reads from .kai/dbt.yaml."""
    config = load_config(project_dir=config_dir, env="default")
    assert config.connection == "analytics.duckdb"
    assert config.profile == "dev"


def test_load_config_production_env(config_dir):
    """load_config loads production environment."""
    config = load_config(project_dir=config_dir, env="production")
    assert config.connection == "postgresql://prod-db/analytics"
    assert config.profile == "prod"
    assert config.target == "prod"


def test_load_config_env_override(config_dir, monkeypatch):
    """Environment variables override config file."""
    monkeypatch.setenv("KAI_DBT_CONNECTION", "override.duckdb")
    config = load_config(project_dir=config_dir, env="default")
    assert config.connection == "override.duckdb"


def test_load_config_cli_override(config_dir):
    """CLI arguments override environment and config."""
    config = load_config(
        project_dir=config_dir,
        env="default",
        cli_overrides={"connection": "cli.duckdb"},
    )
    assert config.connection == "cli.duckdb"


def test_load_config_missing_file(tmp_path):
    """load_config returns empty config when file is missing."""
    config = load_config(project_dir=tmp_path)
    assert config.connection is None


def test_load_config_env_selection(config_dir, monkeypatch):
    """KAI_DBT_ENV environment variable selects config environment."""
    monkeypatch.setenv("KAI_DBT_ENV", "production")
    config = load_config(project_dir=config_dir)
    assert config.profile == "prod"


def test_dbt_cli_config_merge():
    """DbtCliConfig.merge_with combines configs correctly."""
    base = DbtCliConfig(connection="base.duckdb", profile="base")
    merged = base.merge_with({"connection": "override.duckdb"})
    assert merged.connection == "override.duckdb"
    assert merged.profile == "base"  # Not overridden


def test_load_config_priority_chain(config_dir, monkeypatch):
    """Full priority chain: CLI > env > config file."""
    monkeypatch.setenv("KAI_DBT_CONNECTION", "env.duckdb")
    monkeypatch.setenv("KAI_DBT_PROFILE", "env_profile")

    config = load_config(
        project_dir=config_dir,
        env="default",
        cli_overrides={"connection": "cli.duckdb"},
    )

    # CLI wins for connection
    assert config.connection == "cli.duckdb"
    # Env wins for profile (no CLI override)
    assert config.profile == "env_profile"
