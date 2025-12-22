"""Tests for dbt project auto-detection."""
import pytest
from pathlib import Path

from kai_code.agents.dbt.config import find_dbt_project, DbtProjectInfo


@pytest.fixture
def dbt_project(tmp_path):
    """Create a minimal dbt project structure."""
    project_dir = tmp_path / "my_project"
    project_dir.mkdir()

    (project_dir / "dbt_project.yml").write_text("""
name: 'test_project'
version: '1.0.0'
config-version: 2
profile: 'test'
model-paths: ["models"]
""")

    models_dir = project_dir / "models"
    models_dir.mkdir()
    (models_dir / "stg_orders.sql").write_text("SELECT 1")

    return project_dir


def test_find_dbt_project_in_current_dir(dbt_project):
    """find_dbt_project finds project in current directory."""
    result = find_dbt_project(dbt_project)
    assert result is not None
    assert result.project_dir == dbt_project
    assert result.project_name == "test_project"


def test_find_dbt_project_in_parent_dir(dbt_project):
    """find_dbt_project finds project in parent directory."""
    subdir = dbt_project / "models" / "staging"
    subdir.mkdir(parents=True)

    result = find_dbt_project(subdir)
    assert result is not None
    assert result.project_dir == dbt_project


def test_find_dbt_project_not_found(tmp_path):
    """find_dbt_project returns None when no project found."""
    result = find_dbt_project(tmp_path)
    assert result is None


def test_dbt_project_info_model_paths(dbt_project):
    """DbtProjectInfo includes model paths."""
    result = find_dbt_project(dbt_project)
    assert result.model_paths == ["models"]


def test_dbt_project_info_profile(dbt_project):
    """DbtProjectInfo includes profile name."""
    result = find_dbt_project(dbt_project)
    assert result.profile == "test"


def test_dbt_project_info_version(dbt_project):
    """DbtProjectInfo includes version."""
    result = find_dbt_project(dbt_project)
    assert result.version == "1.0.0"
