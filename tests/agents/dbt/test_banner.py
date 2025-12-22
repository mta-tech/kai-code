"""Tests for dbt CLI banner."""
import pytest

from kai_code.agents.dbt.banner import (
    DBT_ASCII_BANNER,
    create_startup_info,
    format_schema_summary,
)


def test_banner_exists():
    """ASCII banner is defined."""
    assert DBT_ASCII_BANNER is not None
    assert len(DBT_ASCII_BANNER) > 0


def test_banner_is_multiline():
    """Banner spans multiple lines."""
    assert "\n" in DBT_ASCII_BANNER


def test_create_startup_info_connected():
    """create_startup_info shows connection status when connected."""
    info = create_startup_info(
        db_connected=True,
        db_name="analytics.duckdb",
        table_count=15,
        project_name="my_project",
    )
    assert "analytics.duckdb" in info
    assert "15" in info
    assert "my_project" in info


def test_create_startup_info_not_connected():
    """create_startup_info handles no connection."""
    info = create_startup_info(db_connected=False)
    assert "not connected" in info.lower() or "no database" in info.lower()


def test_create_startup_info_with_profile():
    """create_startup_info shows profile and target."""
    info = create_startup_info(
        db_connected=False,
        project_name="test_project",
        profile="dev",
        target="local",
    )
    assert "dev" in info
    assert "local" in info


def test_format_schema_summary_empty():
    """format_schema_summary handles empty table list."""
    result = format_schema_summary([])
    assert "No tables" in result or "no tables" in result.lower()


def test_format_schema_summary_with_tables():
    """format_schema_summary formats table list."""
    tables = [
        {"name": "orders", "column_count": 10, "row_count": 1000},
        {"name": "customers", "column_count": 5, "row_count": 500},
    ]
    result = format_schema_summary(tables)
    assert "orders" in result
    assert "customers" in result


def test_format_schema_summary_large_row_counts():
    """format_schema_summary formats large numbers with K/M suffixes."""
    tables = [
        {"name": "events", "column_count": 20, "row_count": 1500000},
        {"name": "users", "column_count": 8, "row_count": 45000},
    ]
    result = format_schema_summary(tables)
    assert "1.5M" in result or "1500000" in result
    assert "45" in result  # Either "45K" or "45000"


def test_format_schema_summary_none_row_count():
    """format_schema_summary handles None row counts."""
    tables = [
        {"name": "unknown", "column_count": 3, "row_count": None},
    ]
    result = format_schema_summary(tables)
    assert "unknown" in result
