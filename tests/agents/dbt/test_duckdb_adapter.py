"""Tests for DuckDB adapter."""
import os
import tempfile

import pytest

# Skip if duckdb not installed
duckdb = pytest.importorskip("duckdb")

from kai_code.agents.dbt.adapters.duckdb import DuckDBAdapter
from kai_code.agents.dbt.models import CardinalityInfo, ColumnInfo, QueryResult, TableInfo


@pytest.fixture
def test_db():
    """Create a temporary DuckDB database with test data."""
    with tempfile.NamedTemporaryFile(suffix=".duckdb", delete=False) as f:
        db_path = f.name

    # Delete the empty temp file so DuckDB can create a fresh database
    os.unlink(db_path)

    conn = duckdb.connect(db_path)
    conn.execute(
        """
        CREATE TABLE customers (
            customer_id INTEGER PRIMARY KEY,
            email VARCHAR NOT NULL,
            status VARCHAR,
            created_at DATE
        )
    """
    )
    conn.execute(
        """
        INSERT INTO customers VALUES
        (1, 'alice@example.com', 'active', '2024-01-01'),
        (2, 'bob@example.com', 'active', '2024-01-02'),
        (3, 'carol@example.com', 'inactive', '2024-01-03')
    """
    )
    conn.execute(
        """
        CREATE TABLE orders (
            order_id INTEGER PRIMARY KEY,
            customer_id INTEGER REFERENCES customers(customer_id),
            total DECIMAL(10, 2),
            status VARCHAR
        )
    """
    )
    conn.execute(
        """
        INSERT INTO orders VALUES
        (1, 1, 99.99, 'completed'),
        (2, 1, 149.99, 'completed'),
        (3, 2, 49.99, 'pending')
    """
    )
    conn.close()

    yield db_path

    os.unlink(db_path)


def test_duckdb_adapter_connect(test_db):
    """DuckDBAdapter can connect to a database."""
    adapter = DuckDBAdapter(test_db)
    assert adapter is not None
    adapter.close()


def test_get_tables(test_db):
    """get_tables returns all tables."""
    adapter = DuckDBAdapter(test_db)
    tables = adapter.get_tables()

    assert len(tables) == 2
    table_names = {t.name for t in tables}
    assert "customers" in table_names
    assert "orders" in table_names

    adapter.close()


def test_get_columns(test_db):
    """get_columns returns column info for a table."""
    adapter = DuckDBAdapter(test_db)
    columns = adapter.get_columns("customers")

    assert len(columns) == 4
    col_names = {c.name for c in columns}
    assert "customer_id" in col_names
    assert "email" in col_names

    # Check primary key detection
    pk_col = next(c for c in columns if c.name == "customer_id")
    assert pk_col.is_primary_key is True

    adapter.close()


def test_get_cardinality(test_db):
    """get_cardinality returns cardinality info."""
    adapter = DuckDBAdapter(test_db)
    card = adapter.get_cardinality("customers", "status")

    assert card.distinct_count == 2  # active, inactive
    assert card.total_count == 3
    assert card.is_low_cardinality is True
    assert set(card.sample_values) == {"active", "inactive"}

    adapter.close()


def test_execute_query(test_db):
    """execute_query runs SQL and returns results."""
    adapter = DuckDBAdapter(test_db)
    result = adapter.execute_query("SELECT * FROM customers ORDER BY customer_id")

    assert result.success is True
    assert result.row_count == 3
    assert "customer_id" in result.columns
    assert result.rows[0]["email"] == "alice@example.com"

    adapter.close()


def test_execute_query_with_limit(test_db):
    """execute_query respects limit parameter."""
    adapter = DuckDBAdapter(test_db)
    result = adapter.execute_query("SELECT * FROM customers", limit=2)

    assert result.success is True
    assert result.row_count == 2
    assert result.truncated is True

    adapter.close()


def test_execute_query_error(test_db):
    """execute_query handles errors gracefully."""
    adapter = DuckDBAdapter(test_db)
    result = adapter.execute_query("SELECT * FROM nonexistent_table")

    assert result.success is False
    assert result.error is not None
    assert (
        "nonexistent_table" in result.error.lower()
        or "not exist" in result.error.lower()
        or "not found" in result.error.lower()
    )

    adapter.close()
