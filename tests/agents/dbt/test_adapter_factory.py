"""Tests for adapter factory function."""
import os
import tempfile

import pytest

from kai_code.agents.dbt.adapters import DatabaseAdapter, get_adapter


def test_get_adapter_duckdb_extension():
    """get_adapter returns DuckDBAdapter for .duckdb files."""
    pytest.importorskip("duckdb")

    with tempfile.NamedTemporaryFile(suffix=".duckdb", delete=False) as f:
        db_path = f.name

    # Delete the empty temp file so DuckDB can create a fresh database
    os.unlink(db_path)

    try:
        import duckdb

        conn = duckdb.connect(db_path)
        conn.close()

        adapter = get_adapter(db_path)
        assert adapter is not None
        assert isinstance(adapter, DatabaseAdapter)
        adapter.close()
    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


def test_get_adapter_duckdb_uri():
    """get_adapter returns DuckDBAdapter for duckdb:// URIs."""
    pytest.importorskip("duckdb")

    with tempfile.NamedTemporaryFile(suffix=".duckdb", delete=False) as f:
        db_path = f.name

    # Delete the empty temp file so DuckDB can create a fresh database
    os.unlink(db_path)

    try:
        import duckdb

        conn = duckdb.connect(db_path)
        conn.close()

        adapter = get_adapter(f"duckdb:///{db_path}")
        assert adapter is not None
        adapter.close()
    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


def test_get_adapter_unsupported():
    """get_adapter raises error for unsupported databases."""
    with pytest.raises(ValueError, match="Unsupported"):
        get_adapter("mysql://localhost/db")


def test_get_adapter_db_extension():
    """get_adapter returns DuckDBAdapter for .db files."""
    pytest.importorskip("duckdb")

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    # Delete the empty temp file so DuckDB can create a fresh database
    os.unlink(db_path)

    try:
        import duckdb

        conn = duckdb.connect(db_path)
        conn.close()

        adapter = get_adapter(db_path)
        assert adapter is not None
        assert isinstance(adapter, DatabaseAdapter)
        adapter.close()
    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


def test_get_adapter_sqlite_extension():
    """get_adapter returns SQLiteAdapter for .sqlite files."""
    import sqlite3

    with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as f:
        db_path = f.name

    try:
        conn = sqlite3.connect(db_path)
        conn.close()

        adapter = get_adapter(db_path)
        assert adapter is not None
        assert isinstance(adapter, DatabaseAdapter)
        adapter.close()
    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


def test_get_adapter_sqlite3_extension():
    """get_adapter returns SQLiteAdapter for .sqlite3 files."""
    import sqlite3

    with tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False) as f:
        db_path = f.name

    try:
        conn = sqlite3.connect(db_path)
        conn.close()

        adapter = get_adapter(db_path)
        assert adapter is not None
        assert isinstance(adapter, DatabaseAdapter)
        adapter.close()
    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


def test_get_adapter_sqlite_uri():
    """get_adapter returns SQLiteAdapter for sqlite:// URIs."""
    import sqlite3

    with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as f:
        db_path = f.name

    try:
        conn = sqlite3.connect(db_path)
        conn.close()

        adapter = get_adapter(f"sqlite:///{db_path}")
        assert adapter is not None
        assert isinstance(adapter, DatabaseAdapter)
        adapter.close()
    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)
