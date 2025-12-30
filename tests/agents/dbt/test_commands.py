"""Tests for dbt slash commands."""
import pytest
from unittest.mock import Mock, MagicMock

from kai_code.agents.dbt.commands import (
    DbtCommandHandler,
    parse_dbt_command,
)


@pytest.fixture
def mock_agent():
    """Create a mock DbtAgent."""
    agent = Mock()
    agent.dbt_project_dir = "/path/to/project"
    agent.dbt_profiles_dir = None

    # Mock adapter
    agent.adapter = Mock()

    # Mock TableInfo objects
    table1 = Mock()
    table1.name = "orders"
    table1.schema = "main"
    table1.full_name = "main.orders"
    table1.row_count = 1000
    table1.column_count = 5

    table2 = Mock()
    table2.name = "customers"
    table2.schema = "main"
    table2.full_name = "main.customers"
    table2.row_count = 500
    table2.column_count = 3

    agent.adapter.get_tables.return_value = [table1, table2]

    # Mock ColumnInfo objects
    col1 = Mock()
    col1.name = "order_id"
    col1.data_type = "INTEGER"
    col1.is_primary_key = True
    col1.is_nullable = False

    col2 = Mock()
    col2.name = "customer_id"
    col2.data_type = "INTEGER"
    col2.is_primary_key = False
    col2.is_nullable = False

    agent.adapter.get_columns.return_value = [col1, col2]

    return agent


def test_parse_dbt_command_run():
    """Parse /dbt run command."""
    cmd, args = parse_dbt_command("/dbt run")
    assert cmd == "run"
    assert args == {}


def test_parse_dbt_command_run_with_select():
    """Parse /dbt run with select argument."""
    cmd, args = parse_dbt_command("/dbt run stg_orders")
    assert cmd == "run"
    assert args["select"] == "stg_orders"


def test_parse_dbt_command_test():
    """Parse /dbt test command."""
    cmd, args = parse_dbt_command("/dbt test")
    assert cmd == "test"


def test_parse_dbt_command_compile():
    """Parse /dbt compile command."""
    cmd, args = parse_dbt_command("/dbt compile my_model")
    assert cmd == "compile"
    assert args["model"] == "my_model"


def test_parse_dbt_command_list():
    """Parse /dbt list command."""
    cmd, args = parse_dbt_command("/dbt list")
    assert cmd == "list"


def test_parse_dbt_command_show():
    """Parse /dbt show command."""
    cmd, args = parse_dbt_command("/dbt show my_model")
    assert cmd == "show"
    assert args["model"] == "my_model"


def test_parse_schema_command():
    """Parse /schema command."""
    cmd, args = parse_dbt_command("/schema")
    assert cmd == "schema"


def test_parse_model_command():
    """Parse /model command with name."""
    cmd, args = parse_dbt_command("/model stg_orders")
    assert cmd == "model"
    assert args["name"] == "stg_orders"


def test_parse_help_command():
    """Parse /help command."""
    cmd, args = parse_dbt_command("/help")
    assert cmd == "help"


def test_parse_exit_command():
    """Parse /exit command."""
    cmd, args = parse_dbt_command("/exit")
    assert cmd == "exit"


def test_command_handler_schema(mock_agent):
    """Command handler executes /schema."""
    handler = DbtCommandHandler(mock_agent)
    result = handler.handle("/schema")
    assert result is not None
    assert "orders" in result.lower() or "table" in result.lower()


def test_command_handler_model(mock_agent):
    """Command handler executes /model."""
    handler = DbtCommandHandler(mock_agent)
    result = handler.handle("/model orders")
    assert result is not None
    assert "order_id" in result or "INTEGER" in result


def test_command_handler_model_no_name(mock_agent):
    """Command handler handles /model without name."""
    handler = DbtCommandHandler(mock_agent)
    result = handler.handle("/model")
    # Check for error message with expected format (includes Example or Usage)
    assert "Example" in result or "Usage" in result or "missing" in result.lower()


def test_command_handler_schema_no_adapter():
    """Command handler handles /schema without adapter."""
    agent = Mock()
    agent.adapter = None
    handler = DbtCommandHandler(agent)
    result = handler.handle("/schema")
    assert "No database" in result or "not connected" in result.lower()


def test_command_handler_unknown():
    """Command handler returns None for unknown commands."""
    handler = DbtCommandHandler(Mock())
    result = handler.handle("/unknown_command")
    assert result is None


def test_command_handler_help(mock_agent):
    """Command handler returns help text."""
    handler = DbtCommandHandler(mock_agent)
    result = handler.handle("/help")
    assert result is not None
    assert "/schema" in result or "/dbt" in result
