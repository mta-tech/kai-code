"""Tests for database adapter base class."""
import pytest

from kai_code.agents.dbt.adapters.base import DatabaseAdapter
from kai_code.agents.dbt.models import (
    CardinalityInfo,
    ColumnInfo,
    QueryResult,
    TableInfo,
)


def test_database_adapter_is_abstract():
    """DatabaseAdapter cannot be instantiated directly."""
    with pytest.raises(TypeError):
        DatabaseAdapter()


def test_database_adapter_has_required_methods():
    """DatabaseAdapter defines all required abstract methods."""
    assert hasattr(DatabaseAdapter, "get_tables")
    assert hasattr(DatabaseAdapter, "get_columns")
    assert hasattr(DatabaseAdapter, "get_cardinality")
    assert hasattr(DatabaseAdapter, "execute_query")
    assert hasattr(DatabaseAdapter, "close")


class ConcreteAdapter(DatabaseAdapter):
    """Concrete implementation for testing."""

    def get_tables(self) -> list[TableInfo]:
        return []

    def get_columns(self, table: str) -> list[ColumnInfo]:
        return []

    def get_cardinality(self, table: str, column: str) -> CardinalityInfo:
        return CardinalityInfo(
            table=table,
            column=column,
            distinct_count=0,
            total_count=0,
            sample_values=[],
            is_low_cardinality=True,
        )

    def execute_query(self, sql: str, limit: int = 100) -> QueryResult:
        return QueryResult(
            success=True,
            columns=[],
            rows=[],
            row_count=0,
            truncated=False,
            error=None,
        )

    def close(self) -> None:
        pass


def test_concrete_adapter_can_be_instantiated():
    """Concrete adapter implementations can be created."""
    adapter = ConcreteAdapter()
    assert adapter is not None


def test_concrete_adapter_methods_return_correct_types():
    """Adapter methods return correct types."""
    adapter = ConcreteAdapter()

    tables = adapter.get_tables()
    assert isinstance(tables, list)

    columns = adapter.get_columns("test")
    assert isinstance(columns, list)

    cardinality = adapter.get_cardinality("test", "col")
    assert isinstance(cardinality, CardinalityInfo)

    result = adapter.execute_query("SELECT 1")
    assert isinstance(result, QueryResult)
