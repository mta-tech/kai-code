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

if TYPE_CHECKING:
    pass


def get_adapter(connection_string: str) -> DatabaseAdapter:
    """Create a database adapter based on connection string.

    Args:
        connection_string: Database connection string or path.
            Supports:
            - DuckDB: "path/to/file.duckdb" or "duckdb:///path/to/file.duckdb"
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

    # Check for PostgreSQL URI
    if connection_string.startswith(("postgresql://", "postgres://")):
        return PostgreSQLAdapter(connection_string)

    raise ValueError(
        f"Unsupported database connection string: {connection_string}. "
        "Supported formats: *.duckdb, duckdb://, postgresql://"
    )


__all__ = [
    "DatabaseAdapter",
    "DuckDBAdapter",
    "PostgreSQLAdapter",
    "get_adapter",
    "parse_connection_string",
]
