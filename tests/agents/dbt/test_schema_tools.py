"""Tests for schema introspection tools."""
import json
import os
import tempfile

import pytest

duckdb = pytest.importorskip("duckdb")

from kai_code.agents.dbt.adapters import DuckDBAdapter
from kai_code.agents.dbt.tools.schema_tools import create_schema_tools


@pytest.fixture
def adapter():
    """Create adapter with test data."""
    with tempfile.NamedTemporaryFile(suffix=".duckdb", delete=False) as f:
        db_path = f.name

    # Delete the empty temp file so DuckDB can create a fresh database
    os.unlink(db_path)

    conn = duckdb.connect(db_path)
    conn.execute(
        """
        CREATE TABLE customers (
            id INTEGER PRIMARY KEY,
            email VARCHAR,
            status VARCHAR
        )
    """
    )
    conn.execute(
        "INSERT INTO customers VALUES (1, 'a@b.com', 'active'), (2, 'c@d.com', 'inactive')"
    )
    conn.close()

    adapter = DuckDBAdapter(db_path)
    yield adapter
    adapter.close()
    if os.path.exists(db_path):
        os.unlink(db_path)


def test_create_schema_tools_returns_list(adapter):
    """create_schema_tools returns a list of tools."""
    tools = create_schema_tools(adapter)
    assert isinstance(tools, list)
    assert len(tools) > 0


def test_get_database_schema_tool(adapter):
    """get_database_schema tool returns schema info."""
    tools = create_schema_tools(adapter)
    get_schema = next(t for t in tools if t.name == "get_database_schema")

    result = get_schema.invoke({})
    data = json.loads(result)

    assert data["success"] is True
    assert len(data["tables"]) == 1
    assert data["tables"][0]["name"] == "customers"


def test_get_table_details_tool(adapter):
    """get_table_details tool returns table info."""
    tools = create_schema_tools(adapter)
    get_details = next(t for t in tools if t.name == "get_table_details")

    result = get_details.invoke({"table_name": "customers"})
    data = json.loads(result)

    assert data["success"] is True
    assert data["table"]["name"] == "customers"
    assert len(data["table"]["columns"]) == 3


def test_search_schema_tool(adapter):
    """search_schema tool finds matching tables/columns."""
    tools = create_schema_tools(adapter)
    search = next(t for t in tools if t.name == "search_schema")

    result = search.invoke({"pattern": "*email*"})
    data = json.loads(result)

    assert data["success"] is True
    assert data["total_matches"] > 0


def test_get_column_cardinality_tool(adapter):
    """get_column_cardinality tool returns cardinality info."""
    tools = create_schema_tools(adapter)
    get_card = next(t for t in tools if t.name == "get_column_cardinality")

    result = get_card.invoke({"table_name": "customers", "column_name": "status"})
    data = json.loads(result)

    assert data["success"] is True
    assert data["distinct_count"] == 2
    assert data["is_low_cardinality"] is True
