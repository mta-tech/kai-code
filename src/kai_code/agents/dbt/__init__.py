"""DbtAgent - specialized agent for dbt data engineering."""
from kai_code.agents.dbt.adapters import (
    DatabaseAdapter,
    DuckDBAdapter,
    PostgreSQLAdapter,
    get_adapter,
)
from kai_code.agents.dbt.agent import DbtAgent
from kai_code.agents.dbt.models import (
    CardinalityInfo,
    ColumnInfo,
    ForeignKeyInfo,
    QueryResult,
    TableInfo,
)

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
