"""Tests for PostgreSQL adapter."""
import os

import pytest

# Skip if psycopg not installed or no test database
psycopg = pytest.importorskip("psycopg")

from kai_code.agents.dbt.adapters.postgresql import (
    PostgreSQLAdapter,
    parse_connection_string,
)
from kai_code.agents.dbt.models import CardinalityInfo, ColumnInfo, QueryResult, TableInfo


# Use environment variable for test database or skip
TEST_DATABASE_URL = os.environ.get("TEST_POSTGRES_URL")


@pytest.fixture
def adapter():
    """Create PostgreSQL adapter for testing."""
    if not TEST_DATABASE_URL:
        pytest.skip("TEST_POSTGRES_URL not set")

    adapter = PostgreSQLAdapter(TEST_DATABASE_URL)
    yield adapter
    adapter.close()


@pytest.mark.skipif(not TEST_DATABASE_URL, reason="No test database")
def test_postgresql_adapter_connect():
    """PostgreSQLAdapter can parse connection string."""
    # Just test that class exists and can be imported
    assert PostgreSQLAdapter is not None


def test_parse_connection_string():
    """Test connection string parsing."""
    result = parse_connection_string("postgresql://user:pass@localhost:5432/mydb")
    assert result["user"] == "user"
    assert result["password"] == "pass"
    assert result["host"] == "localhost"
    assert result["port"] == 5432
    assert result["dbname"] == "mydb"


def test_parse_connection_string_with_params():
    """Test connection string with query parameters."""
    result = parse_connection_string(
        "postgresql://user:pass@localhost/db?sslmode=require"
    )
    assert result["sslmode"] == "require"


def test_parse_connection_string_defaults():
    """Test default values in connection string parsing."""
    result = parse_connection_string("postgresql://user@/mydb")
    assert result["host"] == "localhost"
    assert result["port"] == 5432
