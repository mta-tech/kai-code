"""Database adapters for DbtAgent."""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from kai_code.agents.dbt.adapters.base import DatabaseAdapter
from kai_code.agents.dbt.adapters.duckdb import DuckDBAdapter
from kai_code.agents.dbt.adapters.postgresql import (
    PostgreSQLAdapter,
    parse_connection_string,
)
from kai_code.agents.dbt.adapters.sqlite import SQLiteAdapter

if TYPE_CHECKING:
    pass


def get_adapter(connection_string: str) -> DatabaseAdapter:
    """Create a database adapter based on connection string.

    Args:
        connection_string: Database connection string or path.
            Supports:
            - DuckDB: "path/to/file.duckdb" or "duckdb:///path/to/file.duckdb"
            - SQLite: "path/to/file.sqlite", "path/to/file.sqlite3", or "sqlite:///path/to/file"
            - PostgreSQL: "postgresql://user:pass@host:port/database"

    Returns:
        DatabaseAdapter instance.

    Raises:
        ValueError: If the connection string format is not supported.
    """
    # Check for DuckDB file path (ends with .duckdb or .db)
    if connection_string.endswith((".duckdb", ".db")):
        return DuckDBAdapter(connection_string)

    # Check for DuckDB URI
    if connection_string.startswith("duckdb://"):
        # Extract path from URI (duckdb:///path/to/file)
        path = connection_string.replace("duckdb://", "")
        if path.startswith("/"):
            path = path[1:]  # Remove leading slash for absolute paths
        return DuckDBAdapter(path)

    # Check for SQLite file path (ends with .sqlite or .sqlite3)
    if connection_string.endswith((".sqlite", ".sqlite3")):
        return SQLiteAdapter(connection_string)

    # Check for SQLite URI
    if connection_string.startswith("sqlite://"):
        # Extract path from URI (sqlite:///path/to/file)
        path = connection_string.replace("sqlite://", "")
        if path.startswith("/"):
            path = path[1:]  # Remove leading slash for absolute paths
        return SQLiteAdapter(path)

    # Check for PostgreSQL URI
    if connection_string.startswith(("postgresql://", "postgres://")):
        return PostgreSQLAdapter(connection_string)

    raise ValueError(
        f"Unsupported database connection string: {connection_string}. "
        "Supported formats: *.duckdb, duckdb://, *.sqlite, *.sqlite3, sqlite://, postgresql://"
    )


__all__ = [
    "DatabaseAdapter",
    "DuckDBAdapter",
    "PostgreSQLAdapter",
    "SQLiteAdapter",
    "get_adapter",
    "parse_connection_string",
]
