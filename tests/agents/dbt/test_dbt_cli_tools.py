"""Tests for dbt CLI wrapper tools."""
import pytest

from kai_code.agents.dbt.tools.dbt_cli_tools import create_dbt_cli_tools


@pytest.fixture
def dbt_tools(tmp_path):
    """Create dbt CLI tools for testing."""
    # Create minimal dbt project structure
    project_dir = tmp_path / "dbt_project"
    project_dir.mkdir()

    # Create dbt_project.yml
    (project_dir / "dbt_project.yml").write_text(
        """
name: 'test_project'
version: '1.0.0'
config-version: 2
profile: 'test'
model-paths: ["models"]
"""
    )

    # Create models directory
    models_dir = project_dir / "models"
    models_dir.mkdir()

    (models_dir / "test_model.sql").write_text("SELECT 1 as id")

    return create_dbt_cli_tools(project_dir)


def test_create_dbt_cli_tools_returns_list(dbt_tools):
    """create_dbt_cli_tools returns a list of tools."""
    assert isinstance(dbt_tools, list)
    assert len(dbt_tools) >= 4


def test_dbt_list_tool_exists(dbt_tools):
    """dbt_list tool is available."""
    tool_names = [t.name for t in dbt_tools]
    assert "dbt_list" in tool_names


def test_dbt_compile_tool_exists(dbt_tools):
    """dbt_compile tool is available."""
    tool_names = [t.name for t in dbt_tools]
    assert "dbt_compile" in tool_names


def test_dbt_run_tool_exists(dbt_tools):
    """dbt_run tool is available."""
    tool_names = [t.name for t in dbt_tools]
    assert "dbt_run" in tool_names


def test_dbt_test_tool_exists(dbt_tools):
    """dbt_test tool is available."""
    tool_names = [t.name for t in dbt_tools]
    assert "dbt_test" in tool_names


def test_dbt_show_tool_exists(dbt_tools):
    """dbt_show tool is available."""
    tool_names = [t.name for t in dbt_tools]
    assert "dbt_show" in tool_names
