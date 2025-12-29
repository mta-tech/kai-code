"""SQLite database adapter."""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from kai_code.agents.dbt.adapters.base import DatabaseAdapter
from kai_code.agents.dbt.models import (
    CardinalityInfo,
    ColumnInfo,
    QueryResult,
    TableInfo,
)


class SQLiteAdapter(DatabaseAdapter):
    """Database adapter for SQLite."""

    LOW_CARDINALITY_THRESHOLD = 50

    def __init__(self, database_path: str | Path):
        """Initialize SQLite adapter.

        Args:
            database_path: Path to SQLite database file.
        """
        self.database_path = Path(database_path)
        self._conn = sqlite3.connect(str(self.database_path))

    def get_tables(self) -> list[TableInfo]:
        """Get all tables with metadata."""
        raise NotImplementedError("get_tables not yet implemented")

    def get_columns(self, table: str) -> list[ColumnInfo]:
        """Get columns for a specific table."""
        raise NotImplementedError("get_columns not yet implemented")

    def get_cardinality(self, table: str, column: str) -> CardinalityInfo:
        """Get distinct value count and samples for a column."""
        raise NotImplementedError("get_cardinality not yet implemented")

    def execute_query(self, sql: str, limit: int = 100) -> QueryResult:
        """Execute a read-only SQL query."""
        raise NotImplementedError("execute_query not yet implemented")

    def close(self) -> None:
        """Close the database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None
