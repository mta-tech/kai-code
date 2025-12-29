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
        # Query sqlite_master for all user tables (exclude internal sqlite_ tables)
        cursor = self._conn.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
            AND name NOT LIKE 'sqlite_%'
            ORDER BY name
            """
        )
        table_names = [row[0] for row in cursor.fetchall()]

        tables = []
        for table_name in table_names:
            # Get row count
            try:
                count_cursor = self._conn.execute(
                    f'SELECT COUNT(*) FROM "{table_name}"'
                )
                row_count = count_cursor.fetchone()[0]
            except Exception:
                row_count = None

            # Get column count using PRAGMA table_info
            try:
                column_cursor = self._conn.execute(
                    f'PRAGMA table_info("{table_name}")'
                )
                column_count = len(column_cursor.fetchall())
            except Exception:
                column_count = 0

            tables.append(
                TableInfo(
                    name=table_name,
                    schema="main",  # SQLite uses 'main' as default schema
                    full_name=f"main.{table_name}",
                    description=None,  # SQLite doesn't have table comments
                    column_count=column_count,
                    row_count=row_count,
                )
            )

        return tables

    def get_columns(self, table: str) -> list[ColumnInfo]:
        """Get columns for a specific table."""
        # Parse schema.table format
        if "." in table:
            schema, table_name = table.split(".", 1)
        else:
            schema = "main"
            table_name = table

        # Use PRAGMA table_info to get column metadata
        # Returns: (cid, name, type, notnull, dflt_value, pk)
        cursor = self._conn.execute(f'PRAGMA table_info("{table_name}")')
        rows = cursor.fetchall()

        columns = []
        for row in rows:
            cid, col_name, data_type, notnull, dflt_value, pk = row

            # Check cardinality for potential low-cardinality columns
            is_low_card = False
            categories = None
            if data_type.upper() in ("VARCHAR", "TEXT", "CHAR", "STRING"):
                try:
                    card = self.get_cardinality(table, col_name)
                    is_low_card = card.is_low_cardinality
                    categories = card.sample_values if is_low_card else None
                except Exception:
                    pass

            columns.append(
                ColumnInfo(
                    name=col_name,
                    data_type=data_type,
                    description=None,  # SQLite doesn't have column comments
                    is_nullable=notnull == 0,  # notnull=0 means nullable
                    is_primary_key=pk == 1,  # pk=1 means primary key
                    foreign_key=None,  # TODO: Parse FK constraints
                    is_low_cardinality=is_low_card,
                    categories=categories,
                )
            )

        return columns

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
