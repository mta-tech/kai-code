"""PostgreSQL database adapter."""
from __future__ import annotations

from typing import Any
from urllib.parse import parse_qs, urlparse

try:
    import psycopg
except ImportError:
    psycopg = None

from kai_code.agents.dbt.adapters.base import DatabaseAdapter
from kai_code.agents.dbt.models import (
    CardinalityInfo,
    ColumnInfo,
    QueryResult,
    TableInfo,
)


def parse_connection_string(connection_string: str) -> dict[str, Any]:
    """Parse PostgreSQL connection string into components.

    Args:
        connection_string: PostgreSQL connection URL.

    Returns:
        Dictionary with connection parameters.
    """
    parsed = urlparse(connection_string)

    result = {
        "host": parsed.hostname or "localhost",
        "port": parsed.port or 5432,
        "user": parsed.username,
        "password": parsed.password,
        "dbname": parsed.path.lstrip("/") if parsed.path else None,
    }

    # Parse query parameters
    if parsed.query:
        params = parse_qs(parsed.query)
        for key, values in params.items():
            result[key] = values[0] if len(values) == 1 else values

    return result


class PostgreSQLAdapter(DatabaseAdapter):
    """Database adapter for PostgreSQL."""

    LOW_CARDINALITY_THRESHOLD = 50

    def __init__(self, connection_string: str):
        """Initialize PostgreSQL adapter.

        Args:
            connection_string: PostgreSQL connection URL.
        """
        if psycopg is None:
            raise ImportError(
                "psycopg package is required. Install with: pip install psycopg[binary]"
            )

        self._connection_string = connection_string
        self._conn = psycopg.connect(connection_string)

    def get_tables(self) -> list[TableInfo]:
        """Get all tables with metadata."""
        query = """
            SELECT
                table_name,
                table_schema,
                obj_description((table_schema || '.' || table_name)::regclass) as description
            FROM information_schema.tables
            WHERE table_schema NOT IN ('information_schema', 'pg_catalog')
                AND table_type = 'BASE TABLE'
            ORDER BY table_schema, table_name
        """

        with self._conn.cursor() as cur:
            cur.execute(query)
            result = cur.fetchall()

        tables = []
        for row in result:
            table_name, schema, description = row
            full_name = f"{schema}.{table_name}"

            # Get row count (approximate for performance)
            try:
                with self._conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT reltuples::bigint
                        FROM pg_class
                        WHERE relname = %s
                    """,
                        (table_name,),
                    )
                    count_result = cur.fetchone()
                    row_count = count_result[0] if count_result else None
            except Exception:
                row_count = None

            # Get column count
            columns = self.get_columns(full_name)

            tables.append(
                TableInfo(
                    name=table_name,
                    schema=schema,
                    full_name=full_name,
                    description=description,
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
            schema = "public"
            table_name = table

        query = """
            SELECT
                c.column_name,
                c.data_type,
                c.is_nullable,
                col_description((table_schema || '.' || table_name)::regclass, c.ordinal_position) as description,
                CASE WHEN pk.column_name IS NOT NULL THEN true ELSE false END as is_primary_key
            FROM information_schema.columns c
            LEFT JOIN (
                SELECT kcu.column_name
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu
                    ON tc.constraint_name = kcu.constraint_name
                WHERE tc.table_schema = %s
                    AND tc.table_name = %s
                    AND tc.constraint_type = 'PRIMARY KEY'
            ) pk ON c.column_name = pk.column_name
            WHERE c.table_schema = %s AND c.table_name = %s
            ORDER BY c.ordinal_position
        """

        with self._conn.cursor() as cur:
            cur.execute(query, (schema, table_name, schema, table_name))
            result = cur.fetchall()

        columns = []
        for row in result:
            col_name, data_type, is_nullable, description, is_pk = row

            # Check cardinality for string columns
            is_low_card = False
            categories = None
            if data_type.upper() in ("CHARACTER VARYING", "VARCHAR", "TEXT", "CHAR"):
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
                    description=description,
                    is_nullable=is_nullable == "YES",
                    is_primary_key=is_pk,
                    foreign_key=None,  # TODO: Parse FK constraints
                    is_low_cardinality=is_low_card,
                    categories=categories,
                )
            )

        return columns

    def get_cardinality(self, table: str, column: str) -> CardinalityInfo:
        """Get distinct value count and samples for a column."""
        try:
            with self._conn.cursor() as cur:
                # Get counts
                cur.execute(
                    f"""
                    SELECT
                        COUNT(DISTINCT "{column}") as distinct_count,
                        COUNT(*) as total_count
                    FROM {table}
                """
                )
                counts = cur.fetchone()
                distinct_count = counts[0] if counts else 0
                total_count = counts[1] if counts else 0

                # Get sample values
                cur.execute(
                    f"""
                    SELECT DISTINCT "{column}"
                    FROM {table}
                    WHERE "{column}" IS NOT NULL
                    LIMIT 50
                """
                )
                samples = cur.fetchall()
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
            with self._conn.cursor() as cur:
                cur.execute(sql)
                result = cur.fetchall()
                columns = (
                    [desc[0] for desc in cur.description] if cur.description else []
                )

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
