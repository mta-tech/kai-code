"""Tests for SQLite adapter."""
import os
import sqlite3
import tempfile

import pytest

from kai_code.agents.dbt.adapters.sqlite import SQLiteAdapter
from kai_code.agents.dbt.models import CardinalityInfo, ColumnInfo, QueryResult, TableInfo


@pytest.fixture
def test_db():
    """Create a temporary SQLite database with test data."""
    with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as f:
        db_path = f.name

    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE customers (
            customer_id INTEGER PRIMARY KEY,
            email TEXT NOT NULL,
            status TEXT,
            created_at TEXT
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
            total REAL,
            status TEXT
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
    conn.commit()
    conn.close()

    yield db_path

    os.unlink(db_path)


def test_sqlite_adapter_connect(test_db):
    """SQLiteAdapter can connect to a database."""
    adapter = SQLiteAdapter(test_db)
    assert adapter is not None
    adapter.close()


def test_get_tables(test_db):
    """get_tables returns all tables."""
    adapter = SQLiteAdapter(test_db)
    tables = adapter.get_tables()

    assert len(tables) == 2
    table_names = {t.name for t in tables}
    assert "customers" in table_names
    assert "orders" in table_names

    # Verify TableInfo structure
    for table in tables:
        assert isinstance(table, TableInfo)
        assert table.schema == "main"
        assert table.full_name.startswith("main.")

    adapter.close()


def test_get_tables_row_counts(test_db):
    """get_tables returns correct row counts."""
    adapter = SQLiteAdapter(test_db)
    tables = adapter.get_tables()

    customers_table = next(t for t in tables if t.name == "customers")
    orders_table = next(t for t in tables if t.name == "orders")

    assert customers_table.row_count == 3
    assert orders_table.row_count == 3

    adapter.close()


def test_get_tables_column_counts(test_db):
    """get_tables returns correct column counts."""
    adapter = SQLiteAdapter(test_db)
    tables = adapter.get_tables()

    customers_table = next(t for t in tables if t.name == "customers")
    orders_table = next(t for t in tables if t.name == "orders")

    assert customers_table.column_count == 4
    assert orders_table.column_count == 4

    adapter.close()


def test_get_columns(test_db):
    """get_columns returns column info for a table."""
    adapter = SQLiteAdapter(test_db)
    columns = adapter.get_columns("customers")

    assert len(columns) == 4
    col_names = {c.name for c in columns}
    assert "customer_id" in col_names
    assert "email" in col_names
    assert "status" in col_names
    assert "created_at" in col_names

    # Verify ColumnInfo structure
    for col in columns:
        assert isinstance(col, ColumnInfo)

    adapter.close()


def test_get_columns_primary_key(test_db):
    """get_columns correctly identifies primary key columns."""
    adapter = SQLiteAdapter(test_db)
    columns = adapter.get_columns("customers")

    pk_col = next(c for c in columns if c.name == "customer_id")
    assert pk_col.is_primary_key is True

    # Other columns should not be primary keys
    email_col = next(c for c in columns if c.name == "email")
    assert email_col.is_primary_key is False

    adapter.close()


def test_get_columns_nullable(test_db):
    """get_columns correctly identifies nullable columns."""
    adapter = SQLiteAdapter(test_db)
    columns = adapter.get_columns("customers")

    # email is NOT NULL
    email_col = next(c for c in columns if c.name == "email")
    assert email_col.is_nullable is False

    # status is nullable (no NOT NULL constraint)
    status_col = next(c for c in columns if c.name == "status")
    assert status_col.is_nullable is True

    adapter.close()


def test_get_columns_with_schema_prefix(test_db):
    """get_columns works with schema.table format."""
    adapter = SQLiteAdapter(test_db)
    columns = adapter.get_columns("main.customers")

    assert len(columns) == 4
    col_names = {c.name for c in columns}
    assert "customer_id" in col_names

    adapter.close()


def test_get_cardinality(test_db):
    """get_cardinality returns cardinality info."""
    adapter = SQLiteAdapter(test_db)
    card = adapter.get_cardinality("customers", "status")

    assert isinstance(card, CardinalityInfo)
    assert card.distinct_count == 2  # active, inactive
    assert card.total_count == 3
    assert card.is_low_cardinality is True
    assert set(card.sample_values) == {"active", "inactive"}

    adapter.close()


def test_get_cardinality_high_cardinality(test_db):
    """get_cardinality detects high cardinality columns."""
    adapter = SQLiteAdapter(test_db)
    card = adapter.get_cardinality("customers", "email")

    # Each email is unique, but still below threshold of 50
    assert card.distinct_count == 3
    assert card.total_count == 3
    assert card.is_low_cardinality is True  # 3 < 50

    adapter.close()


def test_get_cardinality_with_schema_prefix(test_db):
    """get_cardinality works with schema.table format."""
    adapter = SQLiteAdapter(test_db)
    card = adapter.get_cardinality("main.customers", "status")

    assert card.distinct_count == 2
    assert card.table == "main.customers"
    assert card.column == "status"

    adapter.close()


def test_execute_query(test_db):
    """execute_query runs SQL and returns results."""
    adapter = SQLiteAdapter(test_db)
    result = adapter.execute_query("SELECT * FROM customers ORDER BY customer_id")

    assert isinstance(result, QueryResult)
    assert result.success is True
    assert result.row_count == 3
    assert "customer_id" in result.columns
    assert result.rows[0]["email"] == "alice@example.com"

    adapter.close()


def test_execute_query_with_limit(test_db):
    """execute_query respects limit parameter."""
    adapter = SQLiteAdapter(test_db)
    result = adapter.execute_query("SELECT * FROM customers", limit=2)

    assert result.success is True
    assert result.row_count == 2
    assert result.truncated is True

    adapter.close()


def test_execute_query_no_truncation(test_db):
    """execute_query does not truncate when under limit."""
    adapter = SQLiteAdapter(test_db)
    result = adapter.execute_query("SELECT * FROM customers", limit=10)

    assert result.success is True
    assert result.row_count == 3
    assert result.truncated is False

    adapter.close()


def test_execute_query_error(test_db):
    """execute_query handles errors gracefully."""
    adapter = SQLiteAdapter(test_db)
    result = adapter.execute_query("SELECT * FROM nonexistent_table")

    assert result.success is False
    assert result.error is not None
    assert "nonexistent_table" in result.error.lower() or "no such table" in result.error.lower()

    adapter.close()


def test_execute_query_syntax_error(test_db):
    """execute_query handles syntax errors gracefully."""
    adapter = SQLiteAdapter(test_db)
    result = adapter.execute_query("SELCT * FROM customers")

    assert result.success is False
    assert result.error is not None

    adapter.close()


def test_execute_query_returns_columns(test_db):
    """execute_query returns correct column names."""
    adapter = SQLiteAdapter(test_db)
    result = adapter.execute_query("SELECT customer_id, email FROM customers LIMIT 1")

    assert result.success is True
    assert result.columns == ["customer_id", "email"]
    assert len(result.rows) == 1
    assert "customer_id" in result.rows[0]
    assert "email" in result.rows[0]

    adapter.close()


def test_close(test_db):
    """close properly releases the connection."""
    adapter = SQLiteAdapter(test_db)
    adapter.close()

    # Accessing connection after close should be None
    assert adapter._conn is None


def test_close_multiple_times(test_db):
    """close can be called multiple times without error."""
    adapter = SQLiteAdapter(test_db)
    adapter.close()
    adapter.close()  # Should not raise


def test_empty_table(test_db):
    """Adapter handles empty tables correctly."""
    # Create an empty table
    conn = sqlite3.connect(test_db)
    conn.execute("CREATE TABLE empty_table (id INTEGER PRIMARY KEY, name TEXT)")
    conn.commit()
    conn.close()

    adapter = SQLiteAdapter(test_db)

    # Test get_tables
    tables = adapter.get_tables()
    empty_table = next(t for t in tables if t.name == "empty_table")
    assert empty_table.row_count == 0

    # Test get_columns
    columns = adapter.get_columns("empty_table")
    assert len(columns) == 2

    # Test get_cardinality
    card = adapter.get_cardinality("empty_table", "name")
    assert card.distinct_count == 0
    assert card.total_count == 0
    assert card.sample_values == []

    adapter.close()


def test_table_with_special_characters(test_db):
    """Adapter handles table names with special characters."""
    conn = sqlite3.connect(test_db)
    conn.execute('CREATE TABLE "table-with-dashes" (id INTEGER PRIMARY KEY)')
    conn.execute('INSERT INTO "table-with-dashes" VALUES (1)')
    conn.commit()
    conn.close()

    adapter = SQLiteAdapter(test_db)
    tables = adapter.get_tables()
    special_table = next((t for t in tables if t.name == "table-with-dashes"), None)
    assert special_table is not None
    assert special_table.row_count == 1

    adapter.close()
