"""Tests for DbtAgent class."""
import os
import tempfile

import pytest

duckdb = pytest.importorskip("duckdb")

from kai_code.agent import KaiAgent
from kai_code.agents.dbt.agent import DbtAgent


@pytest.fixture
def test_project(tmp_path):
    """Create a test project with database and dbt structure."""
    # Create database
    db_path = tmp_path / "analytics.duckdb"

    conn = duckdb.connect(str(db_path))
    conn.execute("CREATE TABLE customers (id INTEGER, name VARCHAR)")
    conn.execute("INSERT INTO customers VALUES (1, 'Alice'), (2, 'Bob')")
    conn.close()

    # Create minimal dbt project
    (tmp_path / "dbt_project.yml").write_text(
        """
name: 'test_project'
version: '1.0.0'
config-version: 2
profile: 'test'
model-paths: ["models"]
"""
    )

    models_dir = tmp_path / "models"
    models_dir.mkdir()
    (models_dir / "stg_customers.sql").write_text("SELECT * FROM customers")

    return {
        "root_dir": tmp_path,
        "db_path": db_path,
    }


def test_dbt_agent_inherits_from_kai_agent():
    """DbtAgent is a subclass of KaiAgent."""
    assert issubclass(DbtAgent, KaiAgent)


def test_dbt_agent_init_without_db(tmp_path):
    """DbtAgent can be created without database connection."""
    agent = DbtAgent(root_dir=tmp_path)
    assert agent is not None
    assert agent.adapter is None


def test_dbt_agent_init_with_db(test_project):
    """DbtAgent connects to database when connection provided."""
    agent = DbtAgent(
        root_dir=test_project["root_dir"],
        db_connection=str(test_project["db_path"]),
    )
    assert agent is not None
    assert agent.adapter is not None
    agent.adapter.close()


def test_dbt_agent_has_config_properties(test_project):
    """DbtAgent exposes dbt-specific configuration."""
    agent = DbtAgent(
        root_dir=test_project["root_dir"],
        db_connection=str(test_project["db_path"]),
    )

    assert agent.dbt_project_dir is not None
    assert agent.db_connection == str(test_project["db_path"])

    agent.adapter.close()


def test_dbt_agent_inherits_kai_agent_properties(test_project):
    """DbtAgent has all KaiAgent properties."""
    agent = DbtAgent(
        root_dir=test_project["root_dir"],
        db_connection=str(test_project["db_path"]),
    )

    # Check inherited properties
    assert hasattr(agent, "config")
    assert hasattr(agent, "backend")
    assert hasattr(agent, "thread_id")
    assert hasattr(agent, "run")
    assert hasattr(agent, "stream")
    assert hasattr(agent, "reset")

    agent.adapter.close()


def test_dbt_agent_get_dbt_tools(test_project):
    """DbtAgent provides dbt-specific tools."""
    agent = DbtAgent(
        root_dir=test_project["root_dir"],
        db_connection=str(test_project["db_path"]),
    )

    tools = agent.get_dbt_tools()
    assert len(tools) > 0

    tool_names = [t.name for t in tools]
    # Should have schema tools when adapter is connected
    assert "get_database_schema" in tool_names
    # Should have dbt CLI tools
    assert "dbt_run" in tool_names

    agent.adapter.close()
