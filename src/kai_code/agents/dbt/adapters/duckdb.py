"""DuckDB database adapter."""
from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    import duckdb
except ImportError:
    duckdb = None

from kai_code.agents.dbt.adapters.base import DatabaseAdapter
from kai_code.agents.dbt.models import (
    CardinalityInfo,
    ColumnInfo,
    QueryResult,
    TableInfo,
)


class DuckDBAdapter(DatabaseAdapter):
    """Database adapter for DuckDB."""

    LOW_CARDINALITY_THRESHOLD = 50

    def __init__(self, database_path: str | Path):
        """Initialize DuckDB adapter.

        Args:
            database_path: Path to DuckDB database file.
        """
        if duckdb is None:
            raise ImportError(
                "duckdb package is required. Install with: pip install duckdb"
            )

        self.database_path = Path(database_path)
        self._conn = duckdb.connect(str(self.database_path))

    def get_tables(self) -> list[TableInfo]:
        """Get all tables with metadata."""
        query = """
            SELECT
                table_name,
                table_schema
            FROM information_schema.tables
            WHERE table_schema NOT IN ('information_schema', 'pg_catalog')
            ORDER BY table_schema, table_name
        """
        result = self._conn.execute(query).fetchall()

        tables = []
        for row in result:
            table_name, schema = row
            full_name = f"{schema}.{table_name}" if schema else table_name

            # Get row count
            try:
                count_result = self._conn.execute(
                    f'SELECT COUNT(*) FROM "{schema}"."{table_name}"'
                ).fetchone()
                row_count = count_result[0] if count_result else None
            except Exception:
                row_count = None

            # Get column count
            columns = self.get_columns(table_name)

            tables.append(
                TableInfo(
                    name=table_name,
                    schema=schema or "main",
                    full_name=full_name,
                    description=None,  # DuckDB doesn't have table comments
                    column_count=len(columns),
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

        query = f"""
            SELECT
                column_name,
                data_type,
                is_nullable
            FROM information_schema.columns
            WHERE table_name = '{table_name}'
            ORDER BY ordinal_position
        """
        result = self._conn.execute(query).fetchall()

        # Get primary key info
        pk_columns = self._get_primary_key_columns(table_name)

        columns = []
        for row in result:
            col_name, data_type, is_nullable = row

            # Check cardinality for potential low-cardinality columns
            is_low_card = False
            categories = None
            if data_type.upper() in ("VARCHAR", "TEXT", "CHAR"):
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
                    description=None,
                    is_nullable=is_nullable == "YES",
                    is_primary_key=col_name in pk_columns,
                    foreign_key=None,  # TODO: Parse FK constraints
                    is_low_cardinality=is_low_card,
                    categories=categories,
                )
            )

        return columns

    def _get_primary_key_columns(self, table_name: str) -> set[str]:
        """Get primary key column names for a table."""
        try:
            query = f"""
                SELECT column_name
                FROM information_schema.table_constraints tc
                JOIN information_schema.constraint_column_usage ccu
                    ON tc.constraint_name = ccu.constraint_name
                WHERE tc.table_name = '{table_name}'
                AND tc.constraint_type = 'PRIMARY KEY'
            """
            result = self._conn.execute(query).fetchall()
            return {row[0] for row in result}
        except Exception:
            return set()

    def get_cardinality(self, table: str, column: str) -> CardinalityInfo:
        """Get distinct value count and samples for a column."""
        try:
            # Get counts
            count_query = f"""
                SELECT
                    COUNT(DISTINCT "{column}") as distinct_count,
                    COUNT(*) as total_count
                FROM "{table}"
            """
            counts = self._conn.execute(count_query).fetchone()
            distinct_count = counts[0] if counts else 0
            total_count = counts[1] if counts else 0

            # Get sample values
            sample_query = f"""
                SELECT DISTINCT "{column}"
                FROM "{table}"
                WHERE "{column}" IS NOT NULL
                LIMIT 50
            """
            samples = self._conn.execute(sample_query).fetchall()
            sample_values = [row[0] for row in samples]

            is_low_cardinality = distinct_count <= self.LOW_CARDINALITY_THRESHOLD

            return CardinalityInfo(
                table=table,
                column=column,
                distinct_count=distinct_count,
                total_count=total_count,
                sample_values=sample_values,
                is_low_cardinality=is_low_cardinality,
            )
        except Exception:
            return CardinalityInfo(
                table=table,
                column=column,
                distinct_count=0,
                total_count=0,
                sample_values=[],
                is_low_cardinality=False,
            )

    def execute_query(self, sql: str, limit: int = 100) -> QueryResult:
        """Execute a read-only SQL query."""
        try:
            result = self._conn.execute(sql).fetchall()
            description = self._conn.description

            columns = [desc[0] for desc in description] if description else []

            truncated = len(result) > limit
            result = result[:limit]

            rows = [dict(zip(columns, row)) for row in result]

            return QueryResult(
                success=True,
                columns=columns,
                rows=rows,
                row_count=len(rows),
                truncated=truncated,
                error=None,
            )
        except Exception as e:
            return QueryResult(
                success=False,
                columns=[],
                rows=[],
                row_count=0,
                truncated=False,
                error=str(e),
            )

    def close(self) -> None:
        """Close the database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None
