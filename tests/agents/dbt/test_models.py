"""Tests for DbtAgent data models."""
import pytest

from kai_code.agents.dbt.models import (
    CardinalityInfo,
    ColumnInfo,
    ForeignKeyInfo,
    QueryResult,
    TableInfo,
)


def test_table_info_creation():
    table = TableInfo(
        name="orders",
        schema="public",
        full_name="public.orders",
        description="Customer orders",
        column_count=5,
        row_count=1000,
    )
    assert table.name == "orders"
    assert table.full_name == "public.orders"


def test_column_info_with_foreign_key():
    fk = ForeignKeyInfo(
        reference_table="customers",
        reference_column="customer_id",
    )
    col = ColumnInfo(
        name="customer_id",
        data_type="INTEGER",
        description="FK to customers",
        is_nullable=False,
        is_primary_key=False,
        foreign_key=fk,
        is_low_cardinality=False,
        categories=None,
    )
    assert col.foreign_key.reference_table == "customers"


def test_cardinality_info():
    card = CardinalityInfo(
        table="orders",
        column="status",
        distinct_count=3,
        total_count=1000,
        sample_values=["pending", "completed", "cancelled"],
        is_low_cardinality=True,
    )
    assert card.is_low_cardinality is True
    assert len(card.sample_values) == 3


def test_query_result_success():
    result = QueryResult(
        success=True,
        columns=["id", "name"],
        rows=[{"id": 1, "name": "Alice"}],
        row_count=1,
        truncated=False,
        error=None,
    )
    assert result.success is True
    assert result.error is None


def test_query_result_error():
    result = QueryResult(
        success=False,
        columns=[],
        rows=[],
        row_count=0,
        truncated=False,
        error="Connection failed",
    )
    assert result.success is False
    assert result.error == "Connection failed"
