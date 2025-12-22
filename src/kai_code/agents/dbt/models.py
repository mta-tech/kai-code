"""Data models for DbtAgent."""
from dataclasses import dataclass
from typing import Any


@dataclass
class ForeignKeyInfo:
    """Foreign key reference information."""

    reference_table: str
    reference_column: str


@dataclass
class ColumnInfo:
    """Database column information."""

    name: str
    data_type: str
    description: str | None
    is_nullable: bool
    is_primary_key: bool
    foreign_key: ForeignKeyInfo | None
    is_low_cardinality: bool
    categories: list[str] | None


@dataclass
class TableInfo:
    """Database table information."""

    name: str
    schema: str
    full_name: str
    description: str | None
    column_count: int
    row_count: int | None


@dataclass
class CardinalityInfo:
    """Column cardinality information."""

    table: str
    column: str
    distinct_count: int
    total_count: int
    sample_values: list[Any]
    is_low_cardinality: bool


@dataclass
class QueryResult:
    """SQL query execution result."""

    success: bool
    columns: list[str]
    rows: list[dict[str, Any]]
    row_count: int
    truncated: bool
    error: str | None
