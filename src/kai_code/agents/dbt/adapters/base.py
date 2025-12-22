"""Base database adapter interface."""
from abc import ABC, abstractmethod

from kai_code.agents.dbt.models import (
    CardinalityInfo,
    ColumnInfo,
    QueryResult,
    TableInfo,
)


class DatabaseAdapter(ABC):
    """Abstract base class for database adapters.

    Provides a common interface for database introspection across
    different database backends (DuckDB, PostgreSQL, etc.).
    """

    @abstractmethod
    def get_tables(self) -> list[TableInfo]:
        """Get all tables with metadata.

        Returns:
            List of TableInfo objects with table metadata.
        """
        ...

    @abstractmethod
    def get_columns(self, table: str) -> list[ColumnInfo]:
        """Get columns for a specific table.

        Args:
            table: Table name (can include schema prefix).

        Returns:
            List of ColumnInfo objects.
        """
        ...

    @abstractmethod
    def get_cardinality(self, table: str, column: str) -> CardinalityInfo:
        """Get distinct value count and samples for a column.

        Args:
            table: Table name.
            column: Column name.

        Returns:
            CardinalityInfo with distinct counts and sample values.
        """
        ...

    @abstractmethod
    def execute_query(self, sql: str, limit: int = 100) -> QueryResult:
        """Execute a read-only SQL query.

        Args:
            sql: SQL query to execute.
            limit: Maximum rows to return.

        Returns:
            QueryResult with execution results.
        """
        ...

    @abstractmethod
    def close(self) -> None:
        """Close the database connection."""
        ...
