"""DbtAgent - specialized agent for dbt data engineering."""
from kai_code.agents.dbt.adapters import (
    DatabaseAdapter,
    DuckDBAdapter,
    PostgreSQLAdapter,
    get_adapter,
)
from kai_code.agents.dbt.agent import DbtAgent
from kai_code.agents.dbt.banner import (
    DBT_ASCII_BANNER,
    create_startup_info,
    format_schema_summary,
)
from kai_code.agents.dbt.cli import cli_main, main, parse_args
from kai_code.agents.dbt.commands import DbtCommandHandler, parse_dbt_command
from kai_code.agents.dbt.config import (
    DbtCliConfig,
    DbtProjectInfo,
    find_dbt_project,
    load_config,
)
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
    # CLI
    "cli_main",
    "main",
    "parse_args",
    # Config
    "DbtCliConfig",
    "DbtProjectInfo",
    "load_config",
    "find_dbt_project",
    # Commands
    "DbtCommandHandler",
    "parse_dbt_command",
    # Banner
    "DBT_ASCII_BANNER",
    "create_startup_info",
    "format_schema_summary",
]
