# DbtAgent Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement DbtAgent, a specialized kai-code agent for building end-to-end data pipelines with dbt.

**Architecture:** DbtAgent extends KaiAgent to add database introspection tools (via DuckDB/PostgreSQL adapters), dbt CLI wrappers, MDL/semantic layer tools, and instruction tools. The agent auto-loads a dbt skill and injects dbt knowledge into its system prompt while retaining all generic coding abilities.

**Tech Stack:** Python 3.11+, duckdb, psycopg, dbt-core, langchain, deepagents

**Design Reference:** `docs/plans/2024-12-22-dbt-agent-design.md`
**Documentation Reference:** `docs/dbt-agent/`

---

## Task 1: Create Data Classes

**Files:**
- Create: `src/kai_code/agents/__init__.py`
- Create: `src/kai_code/agents/dbt/__init__.py`
- Create: `src/kai_code/agents/dbt/models.py`
- Test: `tests/agents/dbt/test_models.py`

**Step 1: Create agents package structure**

```bash
mkdir -p src/kai_code/agents/dbt
mkdir -p tests/agents/dbt
touch src/kai_code/agents/__init__.py
touch src/kai_code/agents/dbt/__init__.py
touch tests/agents/__init__.py
touch tests/agents/dbt/__init__.py
```

**Step 2: Write the failing test for data classes**

Create `tests/agents/dbt/test_models.py`:

```python
"""Tests for DbtAgent data models."""
import pytest
from kai_code.agents.dbt.models import (
    TableInfo,
    ColumnInfo,
    ForeignKeyInfo,
    CardinalityInfo,
    QueryResult,
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
```

**Step 3: Run test to verify it fails**

```bash
cd /Users/fitrakacamarga/project/self/bmad-new/kai-code-1
python -m pytest tests/agents/dbt/test_models.py -v
```

Expected: FAIL with "ModuleNotFoundError: No module named 'kai_code.agents'"

**Step 4: Write minimal implementation**

Create `src/kai_code/agents/dbt/models.py`:

```python
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
```

**Step 5: Update package init files**

Create `src/kai_code/agents/__init__.py`:

```python
"""Kai Code specialized agents."""
```

Create `src/kai_code/agents/dbt/__init__.py`:

```python
"""DbtAgent - specialized agent for dbt data engineering."""
from .models import (
    TableInfo,
    ColumnInfo,
    ForeignKeyInfo,
    CardinalityInfo,
    QueryResult,
)

__all__ = [
    "TableInfo",
    "ColumnInfo",
    "ForeignKeyInfo",
    "CardinalityInfo",
    "QueryResult",
]
```

**Step 6: Run test to verify it passes**

```bash
python -m pytest tests/agents/dbt/test_models.py -v
```

Expected: PASS (5 tests)

**Step 7: Commit**

```bash
git add src/kai_code/agents/ tests/agents/
git commit -m "feat(dbt): add data models for DbtAgent"
```

---

## Task 2: Create Database Adapter Base Class

**Files:**
- Create: `src/kai_code/agents/dbt/adapters/__init__.py`
- Create: `src/kai_code/agents/dbt/adapters/base.py`
- Test: `tests/agents/dbt/test_adapters_base.py`

**Step 1: Create adapters directory**

```bash
mkdir -p src/kai_code/agents/dbt/adapters
touch src/kai_code/agents/dbt/adapters/__init__.py
```

**Step 2: Write the failing test**

Create `tests/agents/dbt/test_adapters_base.py`:

```python
"""Tests for database adapter base class."""
import pytest
from abc import ABC
from kai_code.agents.dbt.adapters.base import DatabaseAdapter
from kai_code.agents.dbt.models import TableInfo, ColumnInfo, CardinalityInfo, QueryResult


def test_database_adapter_is_abstract():
    """DatabaseAdapter cannot be instantiated directly."""
    with pytest.raises(TypeError):
        DatabaseAdapter()


def test_database_adapter_has_required_methods():
    """DatabaseAdapter defines all required abstract methods."""
    assert hasattr(DatabaseAdapter, 'get_tables')
    assert hasattr(DatabaseAdapter, 'get_columns')
    assert hasattr(DatabaseAdapter, 'get_cardinality')
    assert hasattr(DatabaseAdapter, 'execute_query')
    assert hasattr(DatabaseAdapter, 'close')


class ConcreteAdapter(DatabaseAdapter):
    """Concrete implementation for testing."""

    def get_tables(self) -> list[TableInfo]:
        return []

    def get_columns(self, table: str) -> list[ColumnInfo]:
        return []

    def get_cardinality(self, table: str, column: str) -> CardinalityInfo:
        return CardinalityInfo(
            table=table, column=column, distinct_count=0,
            total_count=0, sample_values=[], is_low_cardinality=True
        )

    def execute_query(self, sql: str, limit: int = 100) -> QueryResult:
        return QueryResult(
            success=True, columns=[], rows=[],
            row_count=0, truncated=False, error=None
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
```

**Step 3: Run test to verify it fails**

```bash
python -m pytest tests/agents/dbt/test_adapters_base.py -v
```

Expected: FAIL with "ModuleNotFoundError"

**Step 4: Write minimal implementation**

Create `src/kai_code/agents/dbt/adapters/base.py`:

```python
"""Base database adapter interface."""
from abc import ABC, abstractmethod
from ..models import TableInfo, ColumnInfo, CardinalityInfo, QueryResult


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
```

**Step 5: Update adapters init**

Create `src/kai_code/agents/dbt/adapters/__init__.py`:

```python
"""Database adapters for DbtAgent."""
from .base import DatabaseAdapter

__all__ = ["DatabaseAdapter"]
```

**Step 6: Run test to verify it passes**

```bash
python -m pytest tests/agents/dbt/test_adapters_base.py -v
```

Expected: PASS (4 tests)

**Step 7: Commit**

```bash
git add src/kai_code/agents/dbt/adapters/
git add tests/agents/dbt/test_adapters_base.py
git commit -m "feat(dbt): add DatabaseAdapter abstract base class"
```

---

## Task 3: Implement DuckDB Adapter

**Files:**
- Create: `src/kai_code/agents/dbt/adapters/duckdb.py`
- Test: `tests/agents/dbt/test_duckdb_adapter.py`

**Step 1: Write the failing test**

Create `tests/agents/dbt/test_duckdb_adapter.py`:

```python
"""Tests for DuckDB adapter."""
import pytest
import tempfile
import os
from pathlib import Path

# Skip if duckdb not installed
duckdb = pytest.importorskip("duckdb")

from kai_code.agents.dbt.adapters.duckdb import DuckDBAdapter
from kai_code.agents.dbt.models import TableInfo, ColumnInfo, CardinalityInfo, QueryResult


@pytest.fixture
def test_db():
    """Create a temporary DuckDB database with test data."""
    with tempfile.NamedTemporaryFile(suffix=".duckdb", delete=False) as f:
        db_path = f.name

    conn = duckdb.connect(db_path)
    conn.execute("""
        CREATE TABLE customers (
            customer_id INTEGER PRIMARY KEY,
            email VARCHAR NOT NULL,
            status VARCHAR,
            created_at DATE
        )
    """)
    conn.execute("""
        INSERT INTO customers VALUES
        (1, 'alice@example.com', 'active', '2024-01-01'),
        (2, 'bob@example.com', 'active', '2024-01-02'),
        (3, 'carol@example.com', 'inactive', '2024-01-03')
    """)
    conn.execute("""
        CREATE TABLE orders (
            order_id INTEGER PRIMARY KEY,
            customer_id INTEGER REFERENCES customers(customer_id),
            total DECIMAL(10, 2),
            status VARCHAR
        )
    """)
    conn.execute("""
        INSERT INTO orders VALUES
        (1, 1, 99.99, 'completed'),
        (2, 1, 149.99, 'completed'),
        (3, 2, 49.99, 'pending')
    """)
    conn.close()

    yield db_path

    os.unlink(db_path)


def test_duckdb_adapter_connect(test_db):
    """DuckDBAdapter can connect to a database."""
    adapter = DuckDBAdapter(test_db)
    assert adapter is not None
    adapter.close()


def test_get_tables(test_db):
    """get_tables returns all tables."""
    adapter = DuckDBAdapter(test_db)
    tables = adapter.get_tables()

    assert len(tables) == 2
    table_names = {t.name for t in tables}
    assert "customers" in table_names
    assert "orders" in table_names

    adapter.close()


def test_get_columns(test_db):
    """get_columns returns column info for a table."""
    adapter = DuckDBAdapter(test_db)
    columns = adapter.get_columns("customers")

    assert len(columns) == 4
    col_names = {c.name for c in columns}
    assert "customer_id" in col_names
    assert "email" in col_names

    # Check primary key detection
    pk_col = next(c for c in columns if c.name == "customer_id")
    assert pk_col.is_primary_key is True

    adapter.close()


def test_get_cardinality(test_db):
    """get_cardinality returns cardinality info."""
    adapter = DuckDBAdapter(test_db)
    card = adapter.get_cardinality("customers", "status")

    assert card.distinct_count == 2  # active, inactive
    assert card.total_count == 3
    assert card.is_low_cardinality is True
    assert set(card.sample_values) == {"active", "inactive"}

    adapter.close()


def test_execute_query(test_db):
    """execute_query runs SQL and returns results."""
    adapter = DuckDBAdapter(test_db)
    result = adapter.execute_query("SELECT * FROM customers ORDER BY customer_id")

    assert result.success is True
    assert result.row_count == 3
    assert "customer_id" in result.columns
    assert result.rows[0]["email"] == "alice@example.com"

    adapter.close()


def test_execute_query_with_limit(test_db):
    """execute_query respects limit parameter."""
    adapter = DuckDBAdapter(test_db)
    result = adapter.execute_query("SELECT * FROM customers", limit=2)

    assert result.success is True
    assert result.row_count == 2
    assert result.truncated is True

    adapter.close()


def test_execute_query_error(test_db):
    """execute_query handles errors gracefully."""
    adapter = DuckDBAdapter(test_db)
    result = adapter.execute_query("SELECT * FROM nonexistent_table")

    assert result.success is False
    assert result.error is not None
    assert "nonexistent_table" in result.error.lower() or "not exist" in result.error.lower()

    adapter.close()
```

**Step 2: Run test to verify it fails**

```bash
python -m pytest tests/agents/dbt/test_duckdb_adapter.py -v
```

Expected: FAIL with "ModuleNotFoundError"

**Step 3: Write minimal implementation**

Create `src/kai_code/agents/dbt/adapters/duckdb.py`:

```python
"""DuckDB database adapter."""
from __future__ import annotations
from pathlib import Path
from typing import Any

try:
    import duckdb
except ImportError:
    duckdb = None

from .base import DatabaseAdapter
from ..models import (
    TableInfo,
    ColumnInfo,
    ForeignKeyInfo,
    CardinalityInfo,
    QueryResult,
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
            raise ImportError("duckdb package is required. Install with: pip install duckdb")

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

            tables.append(TableInfo(
                name=table_name,
                schema=schema or "main",
                full_name=full_name,
                description=None,  # DuckDB doesn't have table comments
                column_count=len(columns),
                row_count=row_count,
            ))

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

            columns.append(ColumnInfo(
                name=col_name,
                data_type=data_type,
                description=None,
                is_nullable=is_nullable == "YES",
                is_primary_key=col_name in pk_columns,
                foreign_key=None,  # TODO: Parse FK constraints
                is_low_cardinality=is_low_card,
                categories=categories,
            ))

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
        except Exception as e:
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
```

**Step 4: Update adapters init**

Update `src/kai_code/agents/dbt/adapters/__init__.py`:

```python
"""Database adapters for DbtAgent."""
from .base import DatabaseAdapter
from .duckdb import DuckDBAdapter

__all__ = ["DatabaseAdapter", "DuckDBAdapter"]
```

**Step 5: Run test to verify it passes**

```bash
python -m pytest tests/agents/dbt/test_duckdb_adapter.py -v
```

Expected: PASS (8 tests)

**Step 6: Commit**

```bash
git add src/kai_code/agents/dbt/adapters/duckdb.py
git add tests/agents/dbt/test_duckdb_adapter.py
git commit -m "feat(dbt): add DuckDB database adapter"
```

---

## Task 4: Implement PostgreSQL Adapter

**Files:**
- Create: `src/kai_code/agents/dbt/adapters/postgresql.py`
- Test: `tests/agents/dbt/test_postgresql_adapter.py`

**Step 1: Write the failing test**

Create `tests/agents/dbt/test_postgresql_adapter.py`:

```python
"""Tests for PostgreSQL adapter."""
import pytest
import os

# Skip if psycopg not installed or no test database
psycopg = pytest.importorskip("psycopg")

from kai_code.agents.dbt.adapters.postgresql import PostgreSQLAdapter
from kai_code.agents.dbt.models import TableInfo, ColumnInfo, CardinalityInfo, QueryResult


# Use environment variable for test database or skip
TEST_DATABASE_URL = os.environ.get("TEST_POSTGRES_URL")


@pytest.fixture
def adapter():
    """Create PostgreSQL adapter for testing."""
    if not TEST_DATABASE_URL:
        pytest.skip("TEST_POSTGRES_URL not set")

    adapter = PostgreSQLAdapter(TEST_DATABASE_URL)
    yield adapter
    adapter.close()


@pytest.mark.skipif(not TEST_DATABASE_URL, reason="No test database")
def test_postgresql_adapter_connect():
    """PostgreSQLAdapter can parse connection string."""
    # Just test that class exists and can be imported
    assert PostgreSQLAdapter is not None


def test_parse_connection_string():
    """Test connection string parsing."""
    from kai_code.agents.dbt.adapters.postgresql import parse_connection_string

    result = parse_connection_string("postgresql://user:pass@localhost:5432/mydb")
    assert result["user"] == "user"
    assert result["password"] == "pass"
    assert result["host"] == "localhost"
    assert result["port"] == 5432
    assert result["dbname"] == "mydb"


def test_parse_connection_string_with_params():
    """Test connection string with query parameters."""
    from kai_code.agents.dbt.adapters.postgresql import parse_connection_string

    result = parse_connection_string("postgresql://user:pass@localhost/db?sslmode=require")
    assert result["sslmode"] == "require"
```

**Step 2: Run test to verify it fails**

```bash
python -m pytest tests/agents/dbt/test_postgresql_adapter.py -v
```

Expected: FAIL with "ModuleNotFoundError"

**Step 3: Write minimal implementation**

Create `src/kai_code/agents/dbt/adapters/postgresql.py`:

```python
"""PostgreSQL database adapter."""
from __future__ import annotations
from urllib.parse import urlparse, parse_qs
from typing import Any

try:
    import psycopg
except ImportError:
    psycopg = None

from .base import DatabaseAdapter
from ..models import (
    TableInfo,
    ColumnInfo,
    ForeignKeyInfo,
    CardinalityInfo,
    QueryResult,
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
            raise ImportError("psycopg package is required. Install with: pip install psycopg[binary]")

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
                    cur.execute(f"""
                        SELECT reltuples::bigint
                        FROM pg_class
                        WHERE relname = %s
                    """, (table_name,))
                    count_result = cur.fetchone()
                    row_count = count_result[0] if count_result else None
            except Exception:
                row_count = None

            # Get column count
            columns = self.get_columns(full_name)

            tables.append(TableInfo(
                name=table_name,
                schema=schema,
                full_name=full_name,
                description=description,
                column_count=len(columns),
                row_count=row_count,
            ))

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

            columns.append(ColumnInfo(
                name=col_name,
                data_type=data_type,
                description=description,
                is_nullable=is_nullable == "YES",
                is_primary_key=is_pk,
                foreign_key=None,  # TODO: Parse FK constraints
                is_low_cardinality=is_low_card,
                categories=categories,
            ))

        return columns

    def get_cardinality(self, table: str, column: str) -> CardinalityInfo:
        """Get distinct value count and samples for a column."""
        try:
            with self._conn.cursor() as cur:
                # Get counts
                cur.execute(f"""
                    SELECT
                        COUNT(DISTINCT "{column}") as distinct_count,
                        COUNT(*) as total_count
                    FROM {table}
                """)
                counts = cur.fetchone()
                distinct_count = counts[0] if counts else 0
                total_count = counts[1] if counts else 0

                # Get sample values
                cur.execute(f"""
                    SELECT DISTINCT "{column}"
                    FROM {table}
                    WHERE "{column}" IS NOT NULL
                    LIMIT 50
                """)
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
        except Exception as e:
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
                columns = [desc[0] for desc in cur.description] if cur.description else []

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
```

**Step 4: Update adapters init**

Update `src/kai_code/agents/dbt/adapters/__init__.py`:

```python
"""Database adapters for DbtAgent."""
from .base import DatabaseAdapter
from .duckdb import DuckDBAdapter
from .postgresql import PostgreSQLAdapter, parse_connection_string

__all__ = [
    "DatabaseAdapter",
    "DuckDBAdapter",
    "PostgreSQLAdapter",
    "parse_connection_string",
]
```

**Step 5: Run test to verify it passes**

```bash
python -m pytest tests/agents/dbt/test_postgresql_adapter.py -v
```

Expected: PASS (3 tests, some may be skipped)

**Step 6: Commit**

```bash
git add src/kai_code/agents/dbt/adapters/postgresql.py
git add tests/agents/dbt/test_postgresql_adapter.py
git commit -m "feat(dbt): add PostgreSQL database adapter"
```

---

## Task 5: Create Adapter Factory

**Files:**
- Modify: `src/kai_code/agents/dbt/adapters/__init__.py`
- Test: `tests/agents/dbt/test_adapter_factory.py`

**Step 1: Write the failing test**

Create `tests/agents/dbt/test_adapter_factory.py`:

```python
"""Tests for adapter factory function."""
import pytest
import tempfile
import os

from kai_code.agents.dbt.adapters import get_adapter, DatabaseAdapter


def test_get_adapter_duckdb_extension():
    """get_adapter returns DuckDBAdapter for .duckdb files."""
    with tempfile.NamedTemporaryFile(suffix=".duckdb", delete=False) as f:
        db_path = f.name

    try:
        import duckdb
        conn = duckdb.connect(db_path)
        conn.close()

        adapter = get_adapter(db_path)
        assert adapter is not None
        assert isinstance(adapter, DatabaseAdapter)
        adapter.close()
    finally:
        os.unlink(db_path)


def test_get_adapter_duckdb_uri():
    """get_adapter returns DuckDBAdapter for duckdb:// URIs."""
    with tempfile.NamedTemporaryFile(suffix=".duckdb", delete=False) as f:
        db_path = f.name

    try:
        import duckdb
        conn = duckdb.connect(db_path)
        conn.close()

        adapter = get_adapter(f"duckdb:///{db_path}")
        assert adapter is not None
        adapter.close()
    finally:
        os.unlink(db_path)


def test_get_adapter_unsupported():
    """get_adapter raises error for unsupported databases."""
    with pytest.raises(ValueError, match="Unsupported"):
        get_adapter("mysql://localhost/db")
```

**Step 2: Run test to verify it fails**

```bash
python -m pytest tests/agents/dbt/test_adapter_factory.py -v
```

Expected: FAIL with "cannot import name 'get_adapter'"

**Step 3: Write minimal implementation**

Update `src/kai_code/agents/dbt/adapters/__init__.py`:

```python
"""Database adapters for DbtAgent."""
from .base import DatabaseAdapter
from .duckdb import DuckDBAdapter
from .postgresql import PostgreSQLAdapter, parse_connection_string


def get_adapter(connection_string: str) -> DatabaseAdapter:
    """Factory function to get appropriate database adapter.

    Args:
        connection_string: Database connection string or path.

    Returns:
        Appropriate DatabaseAdapter instance.

    Raises:
        ValueError: If database type is not supported.
    """
    conn_lower = connection_string.lower()

    # DuckDB file path
    if conn_lower.endswith(".duckdb") or conn_lower.endswith(".db"):
        return DuckDBAdapter(connection_string)

    # DuckDB URI
    if conn_lower.startswith("duckdb:///"):
        path = connection_string[10:]  # Remove "duckdb:///"
        return DuckDBAdapter(path)

    # PostgreSQL
    if conn_lower.startswith("postgresql://") or conn_lower.startswith("postgres://"):
        return PostgreSQLAdapter(connection_string)

    raise ValueError(
        f"Unsupported database connection: {connection_string}. "
        "Supported: .duckdb files, duckdb:/// URIs, postgresql:// URIs"
    )


__all__ = [
    "DatabaseAdapter",
    "DuckDBAdapter",
    "PostgreSQLAdapter",
    "parse_connection_string",
    "get_adapter",
]
```

**Step 4: Run test to verify it passes**

```bash
python -m pytest tests/agents/dbt/test_adapter_factory.py -v
```

Expected: PASS (3 tests)

**Step 5: Commit**

```bash
git add src/kai_code/agents/dbt/adapters/__init__.py
git add tests/agents/dbt/test_adapter_factory.py
git commit -m "feat(dbt): add adapter factory function"
```

---

## Task 6: Create Schema Tools

**Files:**
- Create: `src/kai_code/agents/dbt/tools/__init__.py`
- Create: `src/kai_code/agents/dbt/tools/schema_tools.py`
- Test: `tests/agents/dbt/test_schema_tools.py`

**Step 1: Create tools directory**

```bash
mkdir -p src/kai_code/agents/dbt/tools
touch src/kai_code/agents/dbt/tools/__init__.py
```

**Step 2: Write the failing test**

Create `tests/agents/dbt/test_schema_tools.py`:

```python
"""Tests for schema introspection tools."""
import pytest
import json
import tempfile
import os

duckdb = pytest.importorskip("duckdb")

from kai_code.agents.dbt.adapters import DuckDBAdapter
from kai_code.agents.dbt.tools.schema_tools import create_schema_tools


@pytest.fixture
def adapter():
    """Create adapter with test data."""
    with tempfile.NamedTemporaryFile(suffix=".duckdb", delete=False) as f:
        db_path = f.name

    conn = duckdb.connect(db_path)
    conn.execute("""
        CREATE TABLE customers (
            id INTEGER PRIMARY KEY,
            email VARCHAR,
            status VARCHAR
        )
    """)
    conn.execute("INSERT INTO customers VALUES (1, 'a@b.com', 'active'), (2, 'c@d.com', 'inactive')")
    conn.close()

    adapter = DuckDBAdapter(db_path)
    yield adapter
    adapter.close()
    os.unlink(db_path)


def test_create_schema_tools_returns_list(adapter):
    """create_schema_tools returns a list of tools."""
    tools = create_schema_tools(adapter)
    assert isinstance(tools, list)
    assert len(tools) > 0


def test_get_database_schema_tool(adapter):
    """get_database_schema tool returns schema info."""
    tools = create_schema_tools(adapter)
    get_schema = next(t for t in tools if t.name == "get_database_schema")

    result = get_schema.invoke({})
    data = json.loads(result)

    assert data["success"] is True
    assert len(data["tables"]) == 1
    assert data["tables"][0]["name"] == "customers"


def test_get_table_details_tool(adapter):
    """get_table_details tool returns table info."""
    tools = create_schema_tools(adapter)
    get_details = next(t for t in tools if t.name == "get_table_details")

    result = get_details.invoke({"table_name": "customers"})
    data = json.loads(result)

    assert data["success"] is True
    assert data["table"]["name"] == "customers"
    assert len(data["table"]["columns"]) == 3


def test_search_schema_tool(adapter):
    """search_schema tool finds matching tables/columns."""
    tools = create_schema_tools(adapter)
    search = next(t for t in tools if t.name == "search_schema")

    result = search.invoke({"pattern": "*email*"})
    data = json.loads(result)

    assert data["success"] is True
    assert data["total_matches"] > 0
```

**Step 3: Run test to verify it fails**

```bash
python -m pytest tests/agents/dbt/test_schema_tools.py -v
```

Expected: FAIL with "ModuleNotFoundError"

**Step 4: Write minimal implementation**

Create `src/kai_code/agents/dbt/tools/schema_tools.py`:

```python
"""Schema introspection tools for DbtAgent."""
from __future__ import annotations
import json
import re
import fnmatch
from typing import Any

from langchain_core.tools import tool

from ..adapters.base import DatabaseAdapter
from ..models import TableInfo, ColumnInfo


def create_schema_tools(adapter: DatabaseAdapter) -> list:
    """Create schema introspection tools bound to an adapter.

    Args:
        adapter: Database adapter instance.

    Returns:
        List of LangChain tools.
    """

    @tool("get_database_schema")
    def get_database_schema(include_samples: bool = False) -> str:
        """Get the complete database schema including all tables, columns, and descriptions.

        IMPORTANT: Call this tool FIRST before writing any SQL queries to understand
        the available tables, columns, data types, and relationships.

        Args:
            include_samples: If True, include sample data rows for each table.

        Returns:
            JSON string with complete database schema information.
        """
        try:
            tables = adapter.get_tables()

            if not tables:
                return json.dumps({
                    "success": False,
                    "error": "No tables found in database."
                })

            schema_info = {
                "success": True,
                "tables": [],
                "filterable_columns": [],
            }

            for table in tables:
                columns = adapter.get_columns(table.name)

                table_info = {
                    "name": table.name,
                    "schema": table.schema,
                    "full_name": table.full_name,
                    "description": table.description,
                    "row_count": table.row_count,
                    "columns": [],
                }

                for col in columns:
                    col_info = {
                        "name": col.name,
                        "type": col.data_type,
                        "description": col.description,
                    }

                    if col.is_primary_key:
                        col_info["primary_key"] = True

                    if col.foreign_key:
                        col_info["foreign_key"] = {
                            "references_table": col.foreign_key.reference_table,
                            "references_column": col.foreign_key.reference_column,
                        }

                    if col.is_low_cardinality and col.categories:
                        col_info["filterable"] = True
                        col_info["allowed_values"] = col.categories

                        schema_info["filterable_columns"].append({
                            "table": table.full_name,
                            "column": col.name,
                            "values": col.categories,
                        })

                    table_info["columns"].append(col_info)

                schema_info["tables"].append(table_info)

            schema_info["summary"] = {
                "total_tables": len(tables),
                "table_names": [t.name for t in tables],
            }

            return json.dumps(schema_info, indent=2, default=str)

        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})

    @tool("get_table_details")
    def get_table_details(table_name: str) -> str:
        """Get detailed information about a specific table.

        Args:
            table_name: Name of the table (e.g., 'users' or 'public.users').

        Returns:
            JSON string with table details including columns and sample data.
        """
        try:
            tables = adapter.get_tables()

            target = None
            for t in tables:
                if t.name == table_name or t.full_name == table_name:
                    target = t
                    break

            if not target:
                return json.dumps({
                    "success": False,
                    "error": f"Table '{table_name}' not found",
                    "available_tables": [t.name for t in tables],
                })

            columns = adapter.get_columns(target.name)

            # Get sample data
            result = adapter.execute_query(f'SELECT * FROM "{target.name}" LIMIT 5')

            return json.dumps({
                "success": True,
                "table": {
                    "name": target.name,
                    "schema": target.schema,
                    "full_name": target.full_name,
                    "description": target.description,
                    "row_count": target.row_count,
                    "columns": [
                        {
                            "name": c.name,
                            "type": c.data_type,
                            "description": c.description,
                            "is_primary_key": c.is_primary_key,
                            "is_nullable": c.is_nullable,
                        }
                        for c in columns
                    ],
                    "sample_data": result.rows if result.success else [],
                },
            }, indent=2, default=str)

        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})

    @tool("get_column_cardinality")
    def get_column_cardinality(table_name: str, column_name: str) -> str:
        """Get distinct value count and samples for a column.

        Args:
            table_name: Table name.
            column_name: Column name.

        Returns:
            JSON with cardinality info and sample values.
        """
        try:
            card = adapter.get_cardinality(table_name, column_name)

            return json.dumps({
                "success": True,
                "table": card.table,
                "column": card.column,
                "distinct_count": card.distinct_count,
                "total_count": card.total_count,
                "is_low_cardinality": card.is_low_cardinality,
                "sample_values": card.sample_values,
            }, indent=2, default=str)

        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})

    @tool("search_schema")
    def search_schema(
        pattern: str,
        search_in: str = "all",
    ) -> str:
        """Search tables and columns using patterns.

        Supports wildcards: '*' matches any characters, '?' matches single character.

        Args:
            pattern: Search pattern (e.g., '*customer*', 'order_*').
            search_in: Where to search - 'tables', 'columns', or 'all'.

        Returns:
            JSON with matching tables and columns.
        """
        try:
            tables = adapter.get_tables()

            # Convert glob pattern to regex
            if '*' not in pattern and '?' not in pattern:
                regex_pattern = f".*{re.escape(pattern)}.*"
            else:
                regex_pattern = fnmatch.translate(pattern).replace(r'\Z', '')

            compiled = re.compile(regex_pattern, re.IGNORECASE)

            matches = {
                "tables": [],
                "columns": [],
            }

            for table in tables:
                # Search table names
                if search_in in ("all", "tables"):
                    if compiled.search(table.name):
                        matches["tables"].append({
                            "name": table.name,
                            "full_name": table.full_name,
                            "description": table.description,
                        })

                # Search columns
                if search_in in ("all", "columns"):
                    columns = adapter.get_columns(table.name)
                    for col in columns:
                        if compiled.search(col.name):
                            matches["columns"].append({
                                "table": table.full_name,
                                "column": col.name,
                                "type": col.data_type,
                            })

            return json.dumps({
                "success": True,
                "pattern": pattern,
                "total_matches": len(matches["tables"]) + len(matches["columns"]),
                "matches": matches,
            }, indent=2)

        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})

    return [
        get_database_schema,
        get_table_details,
        get_column_cardinality,
        search_schema,
    ]
```

**Step 5: Update tools init**

Create `src/kai_code/agents/dbt/tools/__init__.py`:

```python
"""DbtAgent tools."""
from .schema_tools import create_schema_tools

__all__ = ["create_schema_tools"]
```

**Step 6: Run test to verify it passes**

```bash
python -m pytest tests/agents/dbt/test_schema_tools.py -v
```

Expected: PASS (4 tests)

**Step 7: Commit**

```bash
git add src/kai_code/agents/dbt/tools/
git add tests/agents/dbt/test_schema_tools.py
git commit -m "feat(dbt): add schema introspection tools"
```

---

## Task 7: Create dbt CLI Tools

**Files:**
- Create: `src/kai_code/agents/dbt/tools/dbt_cli_tools.py`
- Test: `tests/agents/dbt/test_dbt_cli_tools.py`

**Step 1: Write the failing test**

Create `tests/agents/dbt/test_dbt_cli_tools.py`:

```python
"""Tests for dbt CLI wrapper tools."""
import pytest
import json
from pathlib import Path

from kai_code.agents.dbt.tools.dbt_cli_tools import create_dbt_cli_tools


@pytest.fixture
def dbt_tools(tmp_path):
    """Create dbt CLI tools for testing."""
    # Create minimal dbt project structure
    project_dir = tmp_path / "dbt_project"
    project_dir.mkdir()

    # Create dbt_project.yml
    (project_dir / "dbt_project.yml").write_text("""
name: 'test_project'
version: '1.0.0'
config-version: 2
profile: 'test'
model-paths: ["models"]
""")

    # Create models directory
    models_dir = project_dir / "models"
    models_dir.mkdir()

    (models_dir / "test_model.sql").write_text("SELECT 1 as id")

    return create_dbt_cli_tools(project_dir)


def test_create_dbt_cli_tools_returns_list(dbt_tools):
    """create_dbt_cli_tools returns a list of tools."""
    assert isinstance(dbt_tools, list)
    assert len(dbt_tools) >= 4


def test_dbt_list_tool_exists(dbt_tools):
    """dbt_list tool is available."""
    tool_names = [t.name for t in dbt_tools]
    assert "dbt_list" in tool_names


def test_dbt_compile_tool_exists(dbt_tools):
    """dbt_compile tool is available."""
    tool_names = [t.name for t in dbt_tools]
    assert "dbt_compile" in tool_names


def test_dbt_run_tool_exists(dbt_tools):
    """dbt_run tool is available."""
    tool_names = [t.name for t in dbt_tools]
    assert "dbt_run" in tool_names


def test_dbt_test_tool_exists(dbt_tools):
    """dbt_test tool is available."""
    tool_names = [t.name for t in dbt_tools]
    assert "dbt_test" in tool_names
```

**Step 2: Run test to verify it fails**

```bash
python -m pytest tests/agents/dbt/test_dbt_cli_tools.py -v
```

Expected: FAIL with "ModuleNotFoundError"

**Step 3: Write minimal implementation**

Create `src/kai_code/agents/dbt/tools/dbt_cli_tools.py`:

```python
"""dbt CLI wrapper tools for DbtAgent."""
from __future__ import annotations
import json
import subprocess
import shlex
from pathlib import Path
from typing import Any

from langchain_core.tools import tool


def _run_dbt_command(
    command: list[str],
    project_dir: Path,
    profiles_dir: Path | None = None,
) -> dict[str, Any]:
    """Run a dbt command and return parsed result.

    Args:
        command: dbt command arguments.
        project_dir: Path to dbt project.
        profiles_dir: Optional path to profiles directory.

    Returns:
        Dictionary with success status and output.
    """
    full_command = ["dbt"] + command + ["--project-dir", str(project_dir)]

    if profiles_dir:
        full_command.extend(["--profiles-dir", str(profiles_dir)])

    try:
        result = subprocess.run(
            full_command,
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout
            cwd=str(project_dir),
        )

        return {
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "stdout": "",
            "stderr": "Command timed out after 5 minutes",
            "returncode": -1,
        }
    except FileNotFoundError:
        return {
            "success": False,
            "stdout": "",
            "stderr": "dbt command not found. Ensure dbt is installed.",
            "returncode": -1,
        }
    except Exception as e:
        return {
            "success": False,
            "stdout": "",
            "stderr": str(e),
            "returncode": -1,
        }


def create_dbt_cli_tools(
    project_dir: Path | str,
    profiles_dir: Path | str | None = None,
) -> list:
    """Create dbt CLI wrapper tools.

    Args:
        project_dir: Path to dbt project directory.
        profiles_dir: Optional path to profiles.yml directory.

    Returns:
        List of LangChain tools.
    """
    project_dir = Path(project_dir)
    profiles_dir = Path(profiles_dir) if profiles_dir else None

    @tool("dbt_run")
    def dbt_run(
        select: str | None = None,
        exclude: str | None = None,
        full_refresh: bool = False,
    ) -> str:
        """Run dbt models.

        Args:
            select: Model selection (e.g., '+my_model', 'tag:staging').
            exclude: Models to exclude.
            full_refresh: Force full refresh of incremental models.

        Returns:
            JSON with run results.
        """
        command = ["run"]

        if select:
            command.extend(["--select", select])
        if exclude:
            command.extend(["--exclude", exclude])
        if full_refresh:
            command.append("--full-refresh")

        result = _run_dbt_command(command, project_dir, profiles_dir)

        if result["success"]:
            # Parse output for model counts
            output = result["stdout"]
            return json.dumps({
                "success": True,
                "message": "dbt run completed successfully",
                "output": output,
            }, indent=2)
        else:
            return json.dumps({
                "success": False,
                "error": result["stderr"] or result["stdout"],
                "suggestion": "Check model syntax and dependencies",
            }, indent=2)

    @tool("dbt_test")
    def dbt_test(select: str | None = None) -> str:
        """Run dbt tests.

        Args:
            select: Test selection criteria.

        Returns:
            JSON with test results.
        """
        command = ["test"]

        if select:
            command.extend(["--select", select])

        result = _run_dbt_command(command, project_dir, profiles_dir)

        return json.dumps({
            "success": result["success"],
            "output": result["stdout"],
            "error": result["stderr"] if not result["success"] else None,
        }, indent=2)

    @tool("dbt_compile")
    def dbt_compile(model_name: str | None = None) -> str:
        """Compile dbt models and return generated SQL.

        Args:
            model_name: Specific model to compile.

        Returns:
            JSON with compiled SQL.
        """
        command = ["compile"]

        if model_name:
            command.extend(["--select", model_name])

        result = _run_dbt_command(command, project_dir, profiles_dir)

        return json.dumps({
            "success": result["success"],
            "output": result["stdout"],
            "error": result["stderr"] if not result["success"] else None,
        }, indent=2)

    @tool("dbt_list")
    def dbt_list(
        select: str | None = None,
        resource_type: str | None = None,
    ) -> str:
        """List dbt resources.

        Args:
            select: Selection criteria.
            resource_type: Filter by type (model, test, source, seed, snapshot).

        Returns:
            JSON with resource list.
        """
        command = ["list"]

        if select:
            command.extend(["--select", select])
        if resource_type:
            command.extend(["--resource-type", resource_type])

        result = _run_dbt_command(command, project_dir, profiles_dir)

        if result["success"]:
            resources = [r.strip() for r in result["stdout"].strip().split("\n") if r.strip()]
            return json.dumps({
                "success": True,
                "resources": resources,
                "count": len(resources),
            }, indent=2)
        else:
            return json.dumps({
                "success": False,
                "error": result["stderr"] or result["stdout"],
            }, indent=2)

    @tool("dbt_show")
    def dbt_show(model_name: str, limit: int = 10) -> str:
        """Preview model output.

        Args:
            model_name: Model to preview.
            limit: Number of rows to show.

        Returns:
            JSON with sample data.
        """
        command = ["show", "--select", model_name, "--limit", str(limit)]

        result = _run_dbt_command(command, project_dir, profiles_dir)

        return json.dumps({
            "success": result["success"],
            "output": result["stdout"],
            "error": result["stderr"] if not result["success"] else None,
        }, indent=2)

    return [dbt_run, dbt_test, dbt_compile, dbt_list, dbt_show]
```

**Step 4: Update tools init**

Update `src/kai_code/agents/dbt/tools/__init__.py`:

```python
"""DbtAgent tools."""
from .schema_tools import create_schema_tools
from .dbt_cli_tools import create_dbt_cli_tools

__all__ = ["create_schema_tools", "create_dbt_cli_tools"]
```

**Step 5: Run test to verify it passes**

```bash
python -m pytest tests/agents/dbt/test_dbt_cli_tools.py -v
```

Expected: PASS (5 tests)

**Step 6: Commit**

```bash
git add src/kai_code/agents/dbt/tools/dbt_cli_tools.py
git add tests/agents/dbt/test_dbt_cli_tools.py
git commit -m "feat(dbt): add dbt CLI wrapper tools"
```

---

## Task 8: Create DbtAgent Class

**Files:**
- Create: `src/kai_code/agents/dbt/agent.py`
- Test: `tests/agents/dbt/test_dbt_agent.py`

**Step 1: Write the failing test**

Create `tests/agents/dbt/test_dbt_agent.py`:

```python
"""Tests for DbtAgent class."""
import pytest
import tempfile
import os
from pathlib import Path

duckdb = pytest.importorskip("duckdb")

from kai_code.agents.dbt.agent import DbtAgent
from kai_code.agent import KaiAgent


@pytest.fixture
def test_project(tmp_path):
    """Create a test project with database and dbt structure."""
    # Create database
    db_path = tmp_path / "analytics.duckdb"
    conn = duckdb.connect(str(db_path))
    conn.execute("CREATE TABLE customers (id INTEGER, name VARCHAR)")
    conn.execute("INSERT INTO customers VALUES (1, 'Alice'), (2, 'Bob')")
    conn.close()

    # Create minimal dbt project
    (tmp_path / "dbt_project.yml").write_text("""
name: 'test_project'
version: '1.0.0'
config-version: 2
profile: 'test'
model-paths: ["models"]
""")

    models_dir = tmp_path / "models"
    models_dir.mkdir()
    (models_dir / "stg_customers.sql").write_text("SELECT * FROM customers")

    return {
        "root_dir": tmp_path,
        "db_path": db_path,
    }


def test_dbt_agent_inherits_from_kai_agent():
    """DbtAgent is a subclass of KaiAgent."""
    assert issubclass(DbtAgent, KaiAgent)


def test_dbt_agent_init_without_db(tmp_path):
    """DbtAgent can be created without database connection."""
    agent = DbtAgent(root_dir=tmp_path)
    assert agent is not None
    assert agent.adapter is None


def test_dbt_agent_init_with_db(test_project):
    """DbtAgent connects to database when connection provided."""
    agent = DbtAgent(
        root_dir=test_project["root_dir"],
        db_connection=str(test_project["db_path"]),
    )
    assert agent is not None
    assert agent.adapter is not None
    agent.adapter.close()


def test_dbt_agent_has_config_properties(test_project):
    """DbtAgent exposes dbt-specific configuration."""
    agent = DbtAgent(
        root_dir=test_project["root_dir"],
        db_connection=str(test_project["db_path"]),
    )

    assert agent.dbt_project_dir is not None
    assert agent.db_connection == str(test_project["db_path"])

    agent.adapter.close()


def test_dbt_agent_inherits_kai_agent_properties(test_project):
    """DbtAgent has all KaiAgent properties."""
    agent = DbtAgent(
        root_dir=test_project["root_dir"],
        db_connection=str(test_project["db_path"]),
    )

    # Check inherited properties
    assert hasattr(agent, 'config')
    assert hasattr(agent, 'backend')
    assert hasattr(agent, 'thread_id')
    assert hasattr(agent, 'run')
    assert hasattr(agent, 'stream')
    assert hasattr(agent, 'reset')

    agent.adapter.close()
```

**Step 2: Run test to verify it fails**

```bash
python -m pytest tests/agents/dbt/test_dbt_agent.py -v
```

Expected: FAIL with "ModuleNotFoundError"

**Step 3: Write minimal implementation**

Create `src/kai_code/agents/dbt/agent.py`:

```python
"""DbtAgent - specialized agent for dbt data engineering."""
from __future__ import annotations
from pathlib import Path
from typing import Any

from ...agent import KaiAgent
from .adapters import get_adapter, DatabaseAdapter
from .tools.schema_tools import create_schema_tools
from .tools.dbt_cli_tools import create_dbt_cli_tools


class DbtAgent(KaiAgent):
    """Specialized agent for dbt data engineering.

    Inherits ALL KaiAgent capabilities:
    - File operations (read, write, edit, glob, grep)
    - Shell execution (execute)
    - Patch application (apply_patch)
    - Skills system (.skills/)
    - YOLO/approval modes
    - Session persistence

    Adds dbt-specific capabilities:
    - Schema introspection tools
    - dbt CLI wrapper tools
    - Database adapter connection
    - dbt skill auto-loading
    """

    def __init__(
        self,
        root_dir: str | Path,
        *,
        model: str | None = None,
        db_connection: str | None = None,
        dbt_project_dir: str | Path | None = None,
        dbt_profiles_dir: str | Path | None = None,
        yolo: bool = True,
        system_prompt: str | None = None,
        skills_dir: str = ".skills",
        state_path: str | Path | None = None,
        **kwargs,
    ) -> None:
        """Initialize DbtAgent.

        Args:
            root_dir: Project root directory.
            model: LLM model handle.
            db_connection: Database connection string for introspection.
            dbt_project_dir: dbt project directory (defaults to root_dir).
            dbt_profiles_dir: profiles.yml location (defaults to ~/.dbt).
            yolo: If False, require approval for dbt commands.
            system_prompt: Additional system prompt.
            skills_dir: Skills directory.
            state_path: Session state file path.
            **kwargs: Additional KaiAgent arguments.
        """
        # Build enhanced system prompt with dbt context
        dbt_prompt = self._build_dbt_system_prompt()
        combined_prompt = f"{dbt_prompt}\n\n{system_prompt}" if system_prompt else dbt_prompt

        # Initialize parent KaiAgent
        super().__init__(
            root_dir=root_dir,
            model=model,
            yolo=yolo,
            system_prompt=combined_prompt,
            skills_dir=skills_dir,
            state_path=state_path,
            **kwargs,
        )

        # dbt-specific configuration
        self._db_connection = db_connection
        self._dbt_project_dir = Path(dbt_project_dir) if dbt_project_dir else Path(root_dir)
        self._dbt_profiles_dir = Path(dbt_profiles_dir) if dbt_profiles_dir else None
        self._adapter: DatabaseAdapter | None = None

        # Initialize database adapter if connection provided
        if db_connection:
            self._adapter = get_adapter(db_connection)

    @property
    def adapter(self) -> DatabaseAdapter | None:
        """Database adapter for introspection."""
        return self._adapter

    @property
    def db_connection(self) -> str | None:
        """Database connection string."""
        return self._db_connection

    @property
    def dbt_project_dir(self) -> Path:
        """dbt project directory."""
        return self._dbt_project_dir

    @property
    def dbt_profiles_dir(self) -> Path | None:
        """dbt profiles directory."""
        return self._dbt_profiles_dir

    def _build_dbt_system_prompt(self) -> str:
        """Build dbt-specific system prompt content."""
        return """## dbt Data Engineering Agent

You are a data engineer specializing in dbt. You build production-quality data pipelines.

### Before Implementation
1. Use get_database_schema() to explore available tables
2. Read dbt_docs/ files for detailed dbt documentation
3. Use get_instructions() if available for business rules

### Layer Conventions
- **staging/** (stg_): Views, 1:1 with source, cleaning only
- **intermediate/** (int_): Tables, business logic, not user-facing
- **marts/** (fct_, dim_): Tables, analytics-ready

### Model Checklist
- Config block with materialization
- CTEs for organization
- Explicit column selection (no SELECT *)
- Data type casting
- Tests in schema.yml
"""

    def get_dbt_tools(self) -> list:
        """Get all dbt-specific tools.

        Returns:
            List of LangChain tools.
        """
        tools = []

        # Schema tools (require adapter)
        if self._adapter:
            tools.extend(create_schema_tools(self._adapter))

        # dbt CLI tools
        tools.extend(create_dbt_cli_tools(
            self._dbt_project_dir,
            self._dbt_profiles_dir,
        ))

        return tools
```

**Step 4: Update dbt package init**

Update `src/kai_code/agents/dbt/__init__.py`:

```python
"""DbtAgent - specialized agent for dbt data engineering."""
from .models import (
    TableInfo,
    ColumnInfo,
    ForeignKeyInfo,
    CardinalityInfo,
    QueryResult,
)
from .adapters import (
    DatabaseAdapter,
    DuckDBAdapter,
    PostgreSQLAdapter,
    get_adapter,
)
from .agent import DbtAgent

__all__ = [
    # Agent
    "DbtAgent",
    # Models
    "TableInfo",
    "ColumnInfo",
    "ForeignKeyInfo",
    "CardinalityInfo",
    "QueryResult",
    # Adapters
    "DatabaseAdapter",
    "DuckDBAdapter",
    "PostgreSQLAdapter",
    "get_adapter",
]
```

**Step 5: Update agents package init**

Update `src/kai_code/agents/__init__.py`:

```python
"""Kai Code specialized agents."""
from .dbt import DbtAgent

__all__ = ["DbtAgent"]
```

**Step 6: Run test to verify it passes**

```bash
python -m pytest tests/agents/dbt/test_dbt_agent.py -v
```

Expected: PASS (5 tests)

**Step 7: Commit**

```bash
git add src/kai_code/agents/
git add tests/agents/dbt/test_dbt_agent.py
git commit -m "feat(dbt): add DbtAgent class extending KaiAgent"
```

---

## Task 9: Create dbt Skill Files

**Files:**
- Create: `src/kai_code/skills/dbt/SKILL.md`
- Create: `src/kai_code/skills/dbt/examples/staging_model.sql`
- Create: `src/kai_code/skills/dbt/examples/schema.yml`

**Step 1: Create skill directory structure**

```bash
mkdir -p src/kai_code/skills/dbt/examples
mkdir -p src/kai_code/skills/dbt/templates
mkdir -p src/kai_code/skills/dbt/instructions
```

**Step 2: Create SKILL.md**

Create `src/kai_code/skills/dbt/SKILL.md`:

```markdown
# dbt Data Engineering Agent

## Your Role

You are a senior data engineer specializing in dbt. You build production-quality
data pipelines that are tested, documented, and maintainable.

## Before Implementation

Before writing any dbt model:

1. **Explore the database**
   - Call `get_database_schema()` to understand available tables
   - Call `get_column_cardinality()` for important columns
   - Identify primary keys and relationships

2. **Check documentation**
   - Read relevant files from `dbt_docs/` using file tools
   - Focus on concepts relevant to your task

3. **Review instructions**
   - Call `get_instructions()` if available for business rules
   - Check existing models for patterns

## Layer Conventions

### Staging Layer (stg_)
- Materialized as `view`
- 1:1 mapping with source tables
- Only cleaning and type casting
- Naming: `stg_{source}__{entity}`

### Intermediate Layer (int_)
- Materialized as `table` or `ephemeral`
- Business logic and transformations
- Not exposed to end users
- Naming: `int_{entity}_{verb}`

### Marts Layer
- **Facts (`fct_`)**: Metrics and measures, materialized as `table`
- **Dimensions (`dim_`)**: Descriptive attributes, materialized as `table`
- Naming: `fct_{entity}` or `dim_{entity}`

## Model Checklist

Every model MUST have:

- [ ] Config block with materialization
- [ ] CTEs for organization (source, cleaned, final)
- [ ] Explicit column selection (no `SELECT *`)
- [ ] Data type casting
- [ ] Descriptive column aliases
- [ ] Tests in `schema.yml`
- [ ] Documentation in `schema.yml`

## Testing Requirements

### Staging Models
- `unique` and `not_null` on primary key
- `relationships` test for foreign keys

### Mart Models
- All staging tests plus:
- `accepted_values` for status/type columns
- Custom data quality tests where needed

## Common Patterns

### Standard CTE Structure

```sql
WITH source AS (
    SELECT * FROM {{ source('schema', 'table') }}
),

cleaned AS (
    SELECT
        CAST(id AS INTEGER) AS entity_id,
        TRIM(LOWER(email)) AS email,
        created_at::DATE AS created_date
    FROM source
    WHERE id IS NOT NULL
),

final AS (
    SELECT * FROM cleaned
)

SELECT * FROM final
```

### Incremental Model Pattern

```sql
{{
    config(
        materialized='incremental',
        unique_key='event_id',
        incremental_strategy='merge'
    )
}}

SELECT *
FROM {{ source('events', 'raw_events') }}

{% if is_incremental() %}
WHERE event_timestamp > (SELECT MAX(event_timestamp) FROM {{ this }})
{% endif %}
```

## Workflow

1. **UNDERSTAND**: Explore schema, read docs, check instructions
2. **DESIGN**: Plan layers, identify dependencies, choose materializations
3. **BUILD**: Create models one at a time, compile before run, test immediately
4. **VALIDATE**: Preview results, run full tests, generate docs
```

**Step 3: Create example staging model**

Create `src/kai_code/skills/dbt/examples/staging_model.sql`:

```sql
-- Example staging model following conventions
-- File: models/staging/stg_ecommerce__orders.sql

{{
    config(
        materialized='view',
        tags=['staging', 'ecommerce']
    )
}}

WITH source AS (
    SELECT * FROM {{ source('ecommerce', 'orders') }}
),

cleaned AS (
    SELECT
        -- Primary key
        CAST(order_id AS INTEGER) AS order_id,

        -- Foreign keys
        CAST(customer_id AS INTEGER) AS customer_id,

        -- Attributes
        TRIM(UPPER(status)) AS order_status,
        CAST(total_amount AS DECIMAL(10, 2)) AS total_amount,

        -- Timestamps
        CAST(created_at AS TIMESTAMP) AS created_at,
        CAST(updated_at AS TIMESTAMP) AS updated_at

    FROM source
    WHERE order_id IS NOT NULL
)

SELECT * FROM cleaned
```

**Step 4: Create example schema.yml**

Create `src/kai_code/skills/dbt/examples/schema.yml`:

```yaml
# Example schema.yml with tests and documentation
version: 2

models:
  - name: stg_ecommerce__orders
    description: |
      Cleaned orders from the ecommerce source system.
      One row per order.

    columns:
      - name: order_id
        description: Primary key for orders
        tests:
          - unique
          - not_null

      - name: customer_id
        description: Foreign key to customers
        tests:
          - not_null
          - relationships:
              to: ref('stg_ecommerce__customers')
              field: customer_id

      - name: order_status
        description: Current order status
        tests:
          - not_null
          - accepted_values:
              values: ['PENDING', 'COMPLETED', 'CANCELLED', 'REFUNDED']

      - name: total_amount
        description: Order total in dollars
        tests:
          - not_null

      - name: created_at
        description: When the order was created
        tests:
          - not_null
```

**Step 5: Commit**

```bash
git add src/kai_code/skills/dbt/
git commit -m "feat(dbt): add dbt skill with SKILL.md and examples"
```

---

## Task 10: Update Dependencies and Exports

**Files:**
- Modify: `pyproject.toml`
- Modify: `src/kai_code/__init__.py`

**Step 1: Update pyproject.toml**

Add dbt dependencies to `pyproject.toml`:

```toml
[project.optional-dependencies]
dbt = [
    "duckdb>=0.9.0",
    "psycopg[binary]>=3.0.0",
    "dbt-core>=1.0.0",
]
```

**Step 2: Update main package exports**

Update `src/kai_code/__init__.py` to include DbtAgent:

```python
# Add to existing exports
from .agents import DbtAgent

# Update __all__ to include DbtAgent
```

**Step 3: Commit**

```bash
git add pyproject.toml src/kai_code/__init__.py
git commit -m "feat(dbt): add optional dbt dependencies and exports"
```

---

## Summary

This implementation plan covers:

1. **Task 1**: Data classes (TableInfo, ColumnInfo, etc.)
2. **Task 2**: DatabaseAdapter base class
3. **Task 3**: DuckDB adapter
4. **Task 4**: PostgreSQL adapter
5. **Task 5**: Adapter factory function
6. **Task 6**: Schema introspection tools
7. **Task 7**: dbt CLI wrapper tools
8. **Task 8**: DbtAgent class
9. **Task 9**: dbt skill files
10. **Task 10**: Dependencies and exports

Each task follows TDD with failing tests first, then implementation.

---

**Plan complete and saved to `docs/plans/2024-12-22-dbt-agent-implementation.md`. Two execution options:**

**1. Subagent-Driven (this session)** - I dispatch fresh subagent per task, review between tasks, fast iteration

**2. Parallel Session (separate)** - Open new session with executing-plans, batch execution with checkpoints

**Which approach?**
